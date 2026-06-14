from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
)
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, View

from orders.models import Order

from .forms import (
    AddressForm,
    CustomPasswordChangeForm,
    UserEmailForm,
    UserLoginForm,
    UserProfileForm,
    UserRegistrationForm,
)
from .models import Address, Profile, User


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_orders = Order.objects.filter(user=user)
        context['orders'] = user_orders.prefetch_related('items')[:5]
        context['total_orders'] = user_orders.count()
        context['total_spent'] = user_orders.filter(
            payment_status=Order.PaymentStatus.COMPLETED
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        context['profile'] = getattr(user, 'profile', None)
        context['addresses'] = Address.objects.filter(user=user)[:3]
        return context


class ManagementPortalView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/management_portal.html'


class DashboardDataView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        user_orders = Order.objects.filter(user=user)
        orders_data = []
        for order in user_orders.prefetch_related('items')[:5]:
            orders_data.append({
                'pk': order.pk,
                'order_id': order.order_id,
                'created_at': order.created_at.strftime('%b %d, %Y %H:%M'),
                'order_status': order.order_status,
                'order_status_display': order.get_order_status_display(),
                'total_amount': str(order.total_amount),
                'valid_next_statuses': [
                    {'code': s, 'label': l} for s, l in order.valid_next_statuses
                ],
            })
        return JsonResponse({
            'orders': orders_data,
            'total_orders': user_orders.count(),
            'total_spent': str(user_orders.filter(
                payment_status=Order.PaymentStatus.COMPLETED
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')),
            'addresses_count': Address.objects.filter(user=user).count(),
        })


class RegisterView(CreateView):
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('products:product_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, f"Welcome, {self.object.username}!")
        return response


class UserLoginView(LoginView):
    form_class = UserLoginForm
    template_name = 'accounts/login.html'

    def get_success_url(self):
        next_url = self.request.POST.get(
            'next',
            self.request.GET.get('next', '')
        )
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts=None):
            return next_url
        return reverse_lazy('products:product_list')


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('products:product_list')


class ProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = getattr(self.request.user, 'profile', None)
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


class ProfileEmailUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserEmailForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Email updated.")
        return super().form_valid(form)


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, form.user)
        messages.success(self.request, "Password changed.")
        return response


class AddressListView(LoginRequiredMixin, ListView):
    model = Address
    template_name = 'accounts/address_list.html'
    context_object_name = 'addresses'

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressCreateView(LoginRequiredMixin, CreateView):
    model = Address
    form_class = AddressForm
    template_name = 'accounts/address_form.html'
    success_url = reverse_lazy('accounts:address_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        if form.cleaned_data.get('is_default'):
            Address.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
        messages.success(self.request, "Address added.")
        return super().form_valid(form)


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    model = Address
    form_class = AddressForm
    template_name = 'accounts/address_form.html'
    success_url = reverse_lazy('accounts:address_list')

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def form_valid(self, form):
        if form.cleaned_data.get('is_default'):
            Address.objects.filter(user=self.request.user, is_default=True).exclude(
                id=self.object.id
            ).update(is_default=False)
        messages.success(self.request, "Address updated.")
        return super().form_valid(form)


class AddressDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.delete()
        messages.success(request, "Address deleted.")
        return redirect('accounts:address_list')
