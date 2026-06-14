from django.contrib import admin
from django.utils.html import format_html

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'product_price', 'quantity', 'total']
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = [
        'order_id', 'customer', 'total_amount_display',
        'payment_badge', 'status_badge', 'item_count', 'created_at',
    ]
    list_display_links = ['order_id']
    list_filter = [
        'order_status', 'payment_status', 'created_at',
        ('order_status', admin.ChoicesFieldListFilter),
    ]
    search_fields = [
        'order_id', 'user__email', 'user__username',
        'mobile_number', 'full_name',
    ]
    readonly_fields = ['order_id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    actions = [
        'mark_confirmed', 'mark_packed', 'mark_shipped',
        'mark_delivered', 'mark_cancelled',
    ]
    save_on_top = True

    fieldsets = [
        ('Order Info', {
            'fields': [
                'order_id', 'user', 'full_name',
                'mobile_number', 'address', 'notes',
            ],
        }),
        ('Pricing', {
            'fields': ['total_amount'],
        }),
        ('Status', {
            'fields': [
                ('order_status', 'payment_status'),
            ],
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    def customer(self, obj):
        return obj.full_name or obj.user.email
    customer.short_description = 'Customer'
    customer.admin_order_field = 'full_name'

    def total_amount_display(self, obj):
        return format_html(
            '<span style="font-weight: bold;">₹{}</span>',
            obj.total_amount,
        )
    total_amount_display.short_description = 'Total'
    total_amount_display.admin_order_field = 'total_amount'

    def payment_badge(self, obj):
        colors = {
            'completed': ('#28a745', 'Completed'),
            'pending': ('#ffc107', 'Pending'),
            'failed': ('#dc3545', 'Failed'),
            'refunded': ('#6c757d', 'Refunded'),
        }
        color, label = colors.get(obj.payment_status, ('#6c757d', obj.payment_status))
        return format_html(
            '<span style="background: {}; color: #fff; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, label,
        )
    payment_badge.short_description = 'Payment'

    def status_badge(self, obj):
        colors = {
            'pending': ('#ffc107', 'Pending'),
            'confirmed': ('#17a2b8', 'Confirmed'),
            'packed': ('#007bff', 'Packed'),
            'shipped': ('#6f42c1', 'Shipped'),
            'delivered': ('#28a745', 'Delivered'),
            'cancelled': ('#dc3545', 'Cancelled'),
        }
        color, label = colors.get(obj.order_status, ('#6c757d', obj.order_status))
        return format_html(
            '<span style="background: {}; color: #fff; padding: 2px 10px; border-radius: 10px; font-size: 11px; font-weight: 600;">{}</span>',
            color, label,
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'order_status'

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'

    def mark_confirmed(self, request, queryset):
        updated = queryset.filter(order_status='pending').update(order_status='confirmed')
        self.message_user(request, f'{updated} order(s) marked as Confirmed.')
    mark_confirmed.short_description = 'Mark selected as Confirmed'

    def mark_packed(self, request, queryset):
        updated = queryset.filter(order_status='confirmed').update(order_status='packed')
        self.message_user(request, f'{updated} order(s) marked as Packed.')
    mark_packed.short_description = 'Mark selected as Packed'

    def mark_shipped(self, request, queryset):
        updated = queryset.filter(order_status='packed').update(order_status='shipped')
        self.message_user(request, f'{updated} order(s) marked as Shipped.')
    mark_shipped.short_description = 'Mark selected as Shipped'

    def mark_delivered(self, request, queryset):
        updated = queryset.filter(order_status='shipped').update(order_status='delivered')
        self.message_user(request, f'{updated} order(s) marked as Delivered.')
    mark_delivered.short_description = 'Mark selected as Delivered'

    def mark_cancelled(self, request, queryset):
        updated = queryset.filter(
            order_status__in=['pending', 'confirmed'],
        ).update(order_status='cancelled')
        self.message_user(request, f'{updated} order(s) cancelled.')
    mark_cancelled.short_description = 'Cancel selected orders'
