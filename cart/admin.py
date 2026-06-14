from django.contrib import admin
from django.utils.html import format_html

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'unit_price', 'line_total']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def unit_price(self, obj):
        return format_html('<span>₹{}</span>', obj.unit_price)
    unit_price.short_description = 'Price'

    def line_total(self, obj):
        return format_html(
            '<span style="font-weight: bold;">₹{}</span>',
            obj.total_price,
        )
    line_total.short_description = 'Total'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    inlines = [CartItemInline]
    list_display = [
        'cart_owner', 'item_count', 'total_value', 'age', 'updated_at',
    ]
    list_filter = ['updated_at', 'created_at']
    search_fields = ['user__email', 'user__username', 'session_key']
    readonly_fields = ['user', 'session_key', 'created_at', 'updated_at']
    actions = ['clear_selected_carts', 'mark_abandoned']

    def has_add_permission(self, request):
        return False

    def cart_owner(self, obj):
        if obj.user:
            return format_html(
                '<a href="/admin/accounts/user/{}/change/">{}</a>',
                obj.user.id, obj.user.email,
            )
        return format_html(
            '<span style="color: #999;">Session: {}</span>',
            obj.session_key[:12] + '...',
        )
    cart_owner.short_description = 'Customer'

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'

    def total_value(self, obj):
        return format_html(
            '<span style="font-weight: bold;">₹{}</span>',
            obj.total_price,
        )
    total_value.short_description = 'Total'

    def age(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.updated_at
        if delta.days > 0:
            return f'{delta.days}d ago'
        if delta.seconds // 3600 > 0:
            return f'{delta.seconds // 3600}h ago'
        return f'{delta.seconds // 60}m ago'
    age.short_description = 'Last Active'

    def clear_selected_carts(self, request, queryset):
        count = 0
        for cart in queryset:
            cart.items.all().delete()
            count += 1
        self.message_user(request, f'{count} cart(s) cleared.')
    clear_selected_carts.short_description = 'Clear selected carts'

    def mark_abandoned(self, request, queryset):
        # Soft action: log which carts are likely abandoned (>7 days inactive)
        from django.utils import timezone
        from datetime import timedelta
        abandoned = queryset.filter(updated_at__lte=timezone.now() - timedelta(days=7))
        self.message_user(
            request,
            f'{abandoned.count()} cart(s) are abandoned (inactive >7 days).',
        )
    mark_abandoned.short_description = 'Show abandoned carts (>7 days)'
