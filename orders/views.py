import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView, View
from django.views.generic.edit import FormView

from accounts.models import User
from cart.models import Cart
from products.models import Product

from .forms import CheckoutForm
from .models import Order, OrderItem


class CheckoutView(FormView):
    template_name = 'orders/checkout.html'
    form_class = CheckoutForm
    success_url = reverse_lazy('orders:order_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = Cart.get_cart(self.request)
        context['cart'] = cart
        context['items'] = cart.items.select_related('product').all()
        return context

    def form_valid(self, form):
        with transaction.atomic():
            if self.request.user.is_anonymous:
                session_key = self.request.session.session_key
                if session_key:
                    self.request.session['_anonymous_cart_key'] = session_key
                guest = User.objects.create_user(
                    username=f'guest_{uuid.uuid4().hex[:12]}',
                    password=uuid.uuid4().hex,
                )
                login(self.request, guest)

            cart = Cart.get_cart(self.request)
            if not cart.items.exists():
                messages.error(self.request, 'Your cart is empty.')
                return redirect('cart:cart_detail')

            cart_items = cart.items.select_related('product').all()

            product_ids = [item.product_id for item in cart_items]
            products = Product.objects.select_for_update().filter(id__in=product_ids)
            product_map = {p.id: p for p in products}

            for cart_item in cart_items:
                product = product_map[cart_item.product_id]
                if not product.in_stock or (product.stock is not None and product.stock < cart_item.quantity):
                    available = product.stock if product.stock is not None else 0
                    messages.error(
                        self.request,
                        f'Insufficient stock for {product.name}. Only {available} available.',
                    )
                    return redirect('cart:cart_detail')

            total = sum(
                (product_map[item.product_id].discount_price or product_map[item.product_id].price) * item.quantity
                for item in cart_items
            )

            order = form.save(commit=False)
            order.user = self.request.user
            order.total_amount = total
            order.payment_status = Order.PaymentStatus.PENDING
            order.order_status = Order.OrderStatus.PENDING
            order.save()

            for cart_item in cart_items:
                product = product_map[cart_item.product_id]
                price = product.discount_price or product.price
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_price=price,
                    quantity=cart_item.quantity,
                    total=price * cart_item.quantity,
                )
                if product.stock is not None:
                    product.stock -= cart_item.quantity
                    product.save(update_fields=['stock'])

            cart.items.all().delete()

        payment_method = form.cleaned_data.get('payment_method', 'upi')

        if settings.DEBUG:
            order.payment_status = Order.PaymentStatus.COMPLETED
            order.order_status = Order.OrderStatus.CONFIRMED
            order.save(update_fields=['payment_status', 'order_status'])
            messages.success(
                self.request,
                f'Order {order.order_id} placed successfully! (Payment skipped in development)',
            )
            return redirect('orders:order_detail', pk=order.pk)

        if payment_method == 'upi':
            return redirect('payments:upi_payment', order_id=order.pk)

        return redirect('payments:initiate_payment', order_id=order.pk)


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        return Order.objects.prefetch_related('items')


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.prefetch_related('items')


class OrderStatusUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        new_status = request.POST.get('status')
        if not new_status or new_status not in Order.OrderStatus.values:
            messages.error(request, 'Invalid status.')
            return redirect('dashboard')

        if new_status == Order.OrderStatus.CANCELLED:
            if order.payment_status == Order.PaymentStatus.COMPLETED:
                messages.error(request, 'Paid orders cannot be cancelled online.')
                return redirect('dashboard')
            if not order.can_cancel():
                messages.error(request, f'Order {order.order_id} cannot be cancelled in its current state.')
                return redirect('dashboard')
            for item in order.items.all():
                if item.product:
                    item.product.stock += item.quantity
                    item.product.save(update_fields=['stock'])
            order.order_status = Order.OrderStatus.CANCELLED
            order.save(update_fields=['order_status'])
            messages.success(request, f'Order {order.order_id} cancelled.')
            return redirect('dashboard')

        if order.can_transition_to(new_status):
            order.order_status = new_status
            order.save(update_fields=['order_status'])
            messages.success(request, f'Order {order.order_id} updated to {order.get_order_status_display()}.')
        else:
            messages.error(request, f'Cannot change order {order.order_id} from {order.get_order_status_display()} to selected status.')
        return redirect('dashboard')


class OrderCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        if order.payment_status == Order.PaymentStatus.COMPLETED:
            messages.error(request, 'Paid orders cannot be cancelled online. Please contact support.')
        elif order.can_cancel():
            for item in order.items.all():
                if item.product:
                    item.product.stock += item.quantity
                    item.product.save(update_fields=['stock'])
            order.order_status = Order.OrderStatus.CANCELLED
            order.save(update_fields=['order_status'])
            messages.success(request, f'Order {order.order_id} cancelled.')
        else:
            messages.error(
                request,
                f'Order {order.order_id} cannot be cancelled in its current state.',
            )
        return redirect('orders:order_detail', pk=order.pk)


class OrderDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        order_id_str = order.order_id
        order.delete()
        messages.success(request, f'Order {order_id_str} removed.')
        return redirect('dashboard')
