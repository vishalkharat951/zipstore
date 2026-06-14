import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError, models

logger = logging.getLogger(__name__)


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart',
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.user:
            return f"Cart ({self.user.email})"
        return f"Cart ({self.session_key[:8]}...)"

    @property
    def total_items(self):
        try:
            return sum(item.quantity for item in self.items.all())
        except (ObjectDoesNotExist, AttributeError, TypeError, DatabaseError) as e:
            logger.error('Failed to compute total_items for cart %s: %s', self.pk, e, exc_info=True)
            return 0

    @property
    def total_price(self):
        try:
            return sum(item.total_price for item in self.items.all())
        except (ObjectDoesNotExist, AttributeError, TypeError, DatabaseError) as e:
            logger.error('Failed to compute total_price for cart %s: %s', self.pk, e, exc_info=True)
            return 0

    @classmethod
    def get_cart(cls, request):
        try:
            if request.user.is_authenticated:
                cart, created = cls.objects.get_or_create(user=request.user)
                if created:
                    logger.info('Created cart %s for user %s', cart.pk, request.user.pk)
                session_key = request.session.session_key
                if session_key:
                    cls._merge_session_items(cart, request, session_key)
                return cart
            session_key = request.session.session_key
            if not session_key:
                request.session.save()
                session_key = request.session.session_key
            request.session['_anonymous_cart_key'] = session_key
            cart, created = cls.objects.get_or_create(session_key=session_key)
            if created:
                logger.info('Created cart %s for session %s', cart.pk, session_key[:12])
            return cart
        except DatabaseError as e:
            logger.error('Database error in get_cart: %s', e, exc_info=True)
            raise

    @classmethod
    def _merge_session_items(cls, user_cart, request, session_key):
        keys_to_check = {session_key}
        old_key = request.session.get('_anonymous_cart_key')
        if old_key:
            keys_to_check.add(old_key)
        for key in keys_to_check:
            try:
                session_cart = cls.objects.get(session_key=key)
                if session_cart.pk == user_cart.pk:
                    continue
                logger.info(
                    'Merging cart %s (session %s) into user cart %s',
                    session_cart.pk, key[:12], user_cart.pk,
                )
                for session_item in session_cart.items.select_related('product').all():
                    try:
                        user_item, created = user_cart.items.get_or_create(
                            product=session_item.product,
                            defaults={'quantity': session_item.quantity},
                        )
                        if not created:
                            new_qty = user_item.quantity + session_item.quantity
                            stock = session_item.product.stock
                            if stock is not None:
                                new_qty = min(new_qty, stock)
                            user_item.quantity = new_qty
                            user_item.save()
                    except DatabaseError as e:
                        logger.error('Failed to merge item %s: %s', session_item.pk, e, exc_info=True)
                        continue
                session_cart.items.all().delete()
                session_cart.delete()
                logger.info('Merged and deleted session cart %s', session_cart.pk)
                return
            except cls.DoesNotExist:
                continue
            except DatabaseError as e:
                logger.error('Database error merging session cart with key %s: %s', key[:12], e, exc_info=True)

    def transfer_to_user(self, user):
        self.user = user
        self.session_key = None
        self.save(update_fields=['user', 'session_key'])


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='items'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def unit_price(self):
        try:
            return self.product.discount_price if self.product.discount_price else self.product.price
        except ObjectDoesNotExist:
            logger.warning('CartItem %s has no product, returning 0 unit_price', self.pk)
            return 0

    @property
    def total_price(self):
        try:
            return self.unit_price * self.quantity
        except (TypeError, ObjectDoesNotExist) as e:
            logger.error('Failed to compute total_price for CartItem %s: %s', self.pk, e, exc_info=True)
            return 0
