import base64
import json
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View

from django.conf import settings

from orders.models import Order

from .helpers import (
    PaymentError,
    VerificationError,
    check_payment_status,
    initiate_payment,
    verify_callback,
)
from .models import PaymentTransaction, PhonePeSettings
from .upi import generate_qr_base64, generate_transaction_ref, generate_upi_intent_url

logger = logging.getLogger(__name__)


class InitiatePaymentView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        order = get_object_or_404(
            Order, id=order_id, user=request.user,
            payment_status=Order.PaymentStatus.PENDING,
        )

        if not PhonePeSettings.get_active():
            messages.error(
                request,
                'Payment gateway is not configured. Please try again later.',
            )
            return redirect('orders:order_detail', pk=order.id)

        try:
            payment_url, transaction_id = initiate_payment(order, request)
            return redirect(payment_url)
        except PaymentError as e:
            messages.error(request, f'Payment failed: {e}')
            logger.error(f'Payment initiation failed for order {order.order_id}: {e}')
            return redirect('orders:order_detail', pk=order.id)


@method_decorator(csrf_exempt, name='dispatch')
class PaymentCallbackView(View):
    def post(self, request):
        response_data = request.POST.get('response')
        x_verify = request.headers.get('X-VERIFY')

        if not response_data:
            logger.warning('Callback received without response data.')
            return HttpResponseBadRequest('Missing response data.')

        try:
            callback_json = verify_callback(response_data, x_verify)
        except VerificationError as e:
            logger.error(f'Callback verification failed: {e}')
            return HttpResponseBadRequest(f'Verification failed: {e}')

        data = callback_json.get('data', {})
        transaction_id = data.get('merchantTransactionId', '')
        transaction = PaymentTransaction.objects.filter(
            transaction_id=transaction_id
        ).first()

        if not transaction:
            logger.warning(f'Unknown transaction in callback: {transaction_id}')
            return HttpResponseBadRequest('Unknown transaction.')

        order = transaction.order
        code = callback_json.get('code', '')
        success = callback_json.get('success', False)

        if success and code == 'PAYMENT_SUCCESS':
            transaction.payment_status = PaymentTransaction.PaymentStatus.SUCCESS
            transaction.response_data = callback_json
            transaction.save(update_fields=['payment_status', 'response_data'])

            order.payment_status = Order.PaymentStatus.COMPLETED
            order.order_status = Order.OrderStatus.CONFIRMED
            order.save(update_fields=['payment_status', 'order_status'])
            logger.info(f'Payment success for order {order.order_id}')
        else:
            transaction.payment_status = PaymentTransaction.PaymentStatus.FAILED
            transaction.response_data = callback_json
            transaction.save(update_fields=['payment_status', 'response_data'])

            order.payment_status = Order.PaymentStatus.FAILED
            order.save(update_fields=['payment_status'])

            for item in order.items.all():
                if item.product:
                    item.product.stock += item.quantity
                    item.product.save(update_fields=['stock'])

            logger.info(f'Payment failed for order {order.order_id}: {code}')

        return HttpResponse('OK')


@method_decorator(csrf_exempt, name='dispatch')
class PaymentRedirectView(View):
    def _handle_redirect(self, request, transaction_id):
        if not transaction_id:
            messages.error(request, 'No transaction reference received.')
            return redirect('orders:order_list')

        transaction = PaymentTransaction.objects.filter(
            transaction_id=transaction_id
        ).first()

        if not transaction:
            messages.error(request, 'Transaction not found.')
            return redirect('orders:order_list')

        order = transaction.order

        if transaction.payment_status == PaymentTransaction.PaymentStatus.SUCCESS:
            messages.success(
                request,
                f'Payment successful! Order {order.order_id} is confirmed.',
            )
            return redirect('orders:order_detail', pk=order.pk)

        if transaction.payment_status == PaymentTransaction.PaymentStatus.FAILED:
            messages.error(request, 'Payment failed. Please try again.')
            return redirect('payments:payment_failure', order_id=order.pk)

        try:
            status_data = check_payment_status(transaction_id)
            if status_data:
                success = status_data.get('success', False)
                code = status_data.get('code', '')
                if success and code == 'PAYMENT_SUCCESS':
                    transaction.payment_status = PaymentTransaction.PaymentStatus.SUCCESS
                    transaction.response_data = status_data
                    transaction.save(update_fields=['payment_status', 'response_data'])
                    order.payment_status = Order.PaymentStatus.COMPLETED
                    order.order_status = Order.OrderStatus.CONFIRMED
                    order.save(update_fields=['payment_status', 'order_status'])
                    messages.success(
                        request,
                        f'Payment successful! Order {order.order_id} is confirmed.',
                    )
                    return redirect('orders:order_detail', pk=order.pk)
                else:
                    transaction.payment_status = PaymentTransaction.PaymentStatus.FAILED
                    transaction.response_data = status_data
                    transaction.save(update_fields=['payment_status', 'response_data'])
                    order.payment_status = Order.PaymentStatus.FAILED
                    order.save(update_fields=['payment_status'])
                    messages.error(request, 'Payment failed. Please try again.')
                    return redirect('payments:payment_failure', order_id=order.pk)
        except Exception as e:
            logger.error(f'Payment status check failed for {transaction_id}: {e}')

        messages.info(
            request,
            'Payment status is being processed. Please check your orders shortly.',
        )
        return redirect('orders:order_detail', pk=order.pk)

    def post(self, request):
        transaction_id = request.POST.get('merchantTransactionId', '')
        return self._handle_redirect(request, transaction_id)

    def get(self, request):
        transaction_id = request.GET.get('merchantTransactionId', '')
        return self._handle_redirect(request, transaction_id)


class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'payments/payment_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_id = kwargs.get('order_id')
        order = get_object_or_404(Order, id=order_id, user=self.request.user)
        context['order'] = order
        return context


class PaymentFailureView(LoginRequiredMixin, TemplateView):
    template_name = 'payments/payment_failure.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_id = kwargs.get('order_id')
        order = get_object_or_404(Order, id=order_id, user=self.request.user)
        context['order'] = order
        return context


class UPIPaymentView(LoginRequiredMixin, TemplateView):
    template_name = 'payments/upi_payment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_id = kwargs.get('order_id')
        order = get_object_or_404(
            Order, id=order_id, user=self.request.user,
            payment_status=Order.PaymentStatus.PENDING,
        )

        transaction_ref = generate_transaction_ref(order)
        amount = float(order.total_amount)
        upi_url = generate_upi_intent_url(amount, order.order_id, transaction_ref)
        qr_data_uri = generate_qr_base64(upi_url)

        PaymentTransaction.objects.update_or_create(
            order=order,
            payment_method=PaymentTransaction.PaymentMethod.UPI,
            payment_status=PaymentTransaction.PaymentStatus.PENDING,
            defaults={
                'transaction_id': transaction_ref,
                'response_data': {
                    'upi_url': upi_url,
                    'amount': str(order.total_amount),
                    'order_id': order.order_id,
                },
            },
        )

        context['order'] = order
        context['qr_data_uri'] = qr_data_uri
        context['upi_url'] = upi_url
        context['transaction_ref'] = transaction_ref
        return context

    def post(self, request, order_id):
        order = get_object_or_404(
            Order, id=order_id, user=request.user,
            payment_status=Order.PaymentStatus.PENDING,
        )

        order.payment_status = Order.PaymentStatus.PENDING
        order.save(update_fields=['payment_status'])

        PaymentTransaction.objects.filter(
            order=order, payment_method=PaymentTransaction.PaymentMethod.UPI,
        ).update(
            payment_status=PaymentTransaction.PaymentStatus.PENDING,
        )

        messages.success(
            request,
            f'Payment initiated for Order {order.order_id}. '
            f'Please complete the payment using your UPI app. '
            f'Your order will remain pending until payment is confirmed.',
        )
        return redirect('orders:order_detail', pk=order.pk)
