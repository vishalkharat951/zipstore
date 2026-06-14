from django import template
from django.db.models import Count, Sum

from accounts.models import User
from orders.models import Order
from products.models import Category, Product

register = template.Library()


@register.simple_tag
def get_admin_stats():
    total_revenue = Order.objects.filter(
        payment_status=Order.PaymentStatus.COMPLETED,
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    return {
        'total_orders': Order.objects.count(),
        'total_pending_orders': Order.objects.filter(
            order_status=Order.OrderStatus.PENDING,
        ).count(),
        'total_products': Product.objects.filter(active=True).count(),
        'total_categories': Category.objects.count(),
        'total_customers': User.objects.filter(is_staff=False, is_active=True).count(),
        'total_revenue': float(total_revenue),
        'recent_orders': Order.objects.select_related('user').order_by('-created_at')[:5],
        'low_stock_products': Product.objects.filter(active=True, stock__lte=5)[:5],
    }
