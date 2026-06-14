from django.contrib import admin
from django.utils.html import format_html

from .models import PaymentTransaction, PhonePeSettings


@admin.register(PhonePeSettings)
class PhonePeSettingsAdmin(admin.ModelAdmin):
    list_display = ['merchant_id', 'environment_badge', 'active_badge', 'created_at']
    list_filter = ['environment', 'active']

    fieldsets = [
        ('PhonePe Configuration', {
            'fields': ['merchant_id', ('salt_key', 'salt_index'), 'environment'],
        }),
        ('Callbacks', {
            'fields': ['callback_url'],
            'description': 'Set the callback URL where PhonePe sends payment responses.',
        }),
        ('Status', {
            'fields': ['active'],
        }),
    ]

    def environment_badge(self, obj):
        if obj.environment == 'production':
            return format_html(
                '<span style="background: #28a745; color: #fff; padding: 2px 8px; border-radius: 10px; font-size: 11px;">Production</span>',
            )
        return format_html(
            '<span style="background: #ffc107; color: #333; padding: 2px 8px; border-radius: 10px; font-size: 11px;">UAT / Test</span>',
        )
    environment_badge.short_description = 'Environment'

    def active_badge(self, obj):
        if obj.active:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">&#9679; Active</span>',
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: bold;">&#9679; Inactive</span>',
        )
    active_badge.short_description = 'Status'

    def has_add_permission(self, request):
        if PhonePeSettings.objects.exists():
            return False
        return True


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id_short', 'order_link', 'amount',
        'payment_method_badge', 'payment_badge', 'created_at',
    ]
    list_filter = ['payment_method', 'payment_status', 'created_at']
    search_fields = [
        'transaction_id', 'order__order_id',
        'order__user__email',
    ]
    readonly_fields = [
        'transaction_id', 'order', 'payment_status',
        'response_data', 'created_at', 'updated_at',
    ]
    date_hierarchy = 'created_at'
    list_select_related = ['order__user']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def transaction_id_short(self, obj):
        return obj.transaction_id[:30] + '...' if len(obj.transaction_id) > 30 else obj.transaction_id
    transaction_id_short.short_description = 'Transaction ID'

    def order_link(self, obj):
        return format_html(
            '<a href="/admin/orders/order/{}/change/">{}</a>',
            obj.order.id, obj.order.order_id,
        )
    order_link.short_description = 'Order'

    def payment_method_badge(self, obj):
        colors = {
            'upi': ('#6f42c1', 'UPI'),
            'phonepe': ('#0d6efd', 'PhonePe'),
        }
        color, label = colors.get(obj.payment_method, ('#6c757d', obj.payment_method))
        return format_html(
            '<span style="background: {}; color: #fff; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, label,
        )
    payment_method_badge.short_description = 'Method'

    def amount(self, obj):
        return format_html(
            '<span style="font-weight: bold;">₹{}</span>',
            obj.order.total_amount,
        )
    amount.short_description = 'Amount'

    def payment_badge(self, obj):
        colors = {
            'success': ('#28a745', 'Success'),
            'pending': ('#ffc107', 'Pending'),
            'failed': ('#dc3545', 'Failed'),
            'refunded': ('#6c757d', 'Refunded'),
        }
        color, label = colors.get(obj.payment_status, ('#6c757d', obj.payment_status))
        return format_html(
            '<span style="background: {}; color: #fff; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, label,
        )
    payment_badge.short_description = 'Status'
