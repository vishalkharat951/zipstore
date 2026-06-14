import random
import string
from datetime import datetime

from django.conf import settings
from django.db import models

from products.models import Product


def generate_order_id():
    prefix = 'ORD'
    date_part = datetime.now().strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f'{prefix}-{date_part}-{random_part}'


class Order(models.Model):
    class OrderStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        PACKED = 'packed', 'Packed'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    order_id = models.CharField(
        max_length=30, unique=True, editable=False, default=generate_order_id
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
    )
    full_name = models.CharField(max_length=255, default='')
    mobile_number = models.CharField(max_length=20)
    address = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    order_status = models.CharField(
        max_length=10, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_id

    def can_cancel(self):
        return self.order_status in [
            self.OrderStatus.PENDING,
            self.OrderStatus.CONFIRMED,
        ]

    def can_transition_to(self, new_status):
        valid_transitions = {
            self.OrderStatus.PENDING: [self.OrderStatus.CONFIRMED, self.OrderStatus.CANCELLED],
            self.OrderStatus.CONFIRMED: [self.OrderStatus.PACKED, self.OrderStatus.CANCELLED],
            self.OrderStatus.PACKED: [self.OrderStatus.SHIPPED],
            self.OrderStatus.SHIPPED: [self.OrderStatus.DELIVERED],
            self.OrderStatus.DELIVERED: [],
            self.OrderStatus.CANCELLED: [],
        }
        return new_status in valid_transitions.get(self.order_status, [])

    @property
    def valid_next_statuses(self):
        transitions = []
        mapping = {
            self.OrderStatus.CONFIRMED: 'Confirmed',
            self.OrderStatus.PACKED: 'Packed',
            self.OrderStatus.SHIPPED: 'Shipped',
            self.OrderStatus.DELIVERED: 'Delivered',
        }
        for status, label in mapping.items():
            if self.can_transition_to(status):
                transitions.append((status, label))
        if self.can_transition_to(self.OrderStatus.CANCELLED) and self.payment_status != self.PaymentStatus.COMPLETED:
            transitions.append((self.OrderStatus.CANCELLED, 'Cancel'))
        return transitions


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items'
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, related_name='order_items'
    )
    product_name = models.CharField(max_length=255)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"
