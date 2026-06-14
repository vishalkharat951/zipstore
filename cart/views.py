import logging

from django.contrib import messages
from django.db import DatabaseError, IntegrityError
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, View

from products.models import Product

from .models import Cart, CartItem

MAX_QUANTITY_PER_ITEM = 99

logger = logging.getLogger(__name__)


class CartDetailView(TemplateView):
    template_name = 'cart/cart_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            cart = Cart.get_cart(self.request)
            context['cart'] = cart
            context['items'] = cart.items.select_related('product__category').all()
            context['max_quantity_per_item'] = MAX_QUANTITY_PER_ITEM
        except DatabaseError as e:
            logger.error('CartDetailView failed to load cart: %s', e, exc_info=True)
            context['cart'] = None
            context['items'] = []
            context['max_quantity_per_item'] = MAX_QUANTITY_PER_ITEM
        return context


@method_decorator(require_POST, name='dispatch')
class AddToCartView(View):
    def post(self, request, product_id):
        if not isinstance(product_id, int) or product_id < 1:
            logger.warning('Invalid product_id %s in AddToCartView', product_id)
            messages.error(request, 'Invalid product ID.')
            return redirect('cart:cart_detail')

        try:
            product = get_object_or_404(Product, id=product_id, active=True)
        except Http404:
            logger.warning('AddToCartView: product %s not found or inactive', product_id)
            messages.error(request, 'Product not found.')
            return redirect('cart:cart_detail')

        if not product.in_stock or (product.stock is not None and product.stock < 1):
            messages.error(request, f'{product.name} is out of stock.')
            return redirect('cart:cart_detail')

        try:
            cart = Cart.get_cart(request)
        except DatabaseError as e:
            logger.error('AddToCartView: failed to get cart for product %s: %s', product_id, e, exc_info=True)
            messages.error(request, 'A database error occurred. Please try again.')
            return redirect('cart:cart_detail')

        try:
            item, created = CartItem.objects.get_or_create(
                cart=cart, product=product,
                defaults={'quantity': 1},
            )
        except IntegrityError as e:
            logger.warning('AddToCartView: IntegrityError for product %s in cart %s: %s', product_id, cart.pk, e)
            messages.error(request, 'Could not add item to cart. Please try again.')
            return redirect('cart:cart_detail')
        except DatabaseError as e:
            logger.error('AddToCartView: DatabaseError for product %s: %s', product_id, e, exc_info=True)
            messages.error(request, 'A database error occurred. Please try again.')
            return redirect('cart:cart_detail')

        if not created:
            if product.stock is None or item.quantity < product.stock:
                if item.quantity >= MAX_QUANTITY_PER_ITEM:
                    messages.warning(request, f'Maximum {MAX_QUANTITY_PER_ITEM} items per product.')
                    return redirect('cart:cart_detail')
                item.quantity += 1
                try:
                    item.save()
                except DatabaseError as e:
                    logger.error('AddToCartView: failed to save quantity for item %s: %s', item.pk, e, exc_info=True)
                    messages.error(request, 'Could not update quantity. Please try again.')
                    return redirect('cart:cart_detail')
                messages.success(request, f"Updated {product.name} quantity to {item.quantity}.")
                logger.info('Incremented quantity for product %s in cart %s to %s', product_id, cart.pk, item.quantity)
            else:
                messages.warning(request, f"Cannot add more {product.name}. Stock limit reached.")
        else:
            messages.success(request, f"{product.name} added to cart.")
            logger.info('Added product %s to cart %s', product_id, cart.pk)

        next_url = request.POST.get('next')
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts=None):
            return redirect(next_url)
        return redirect('cart:cart_detail')


@method_decorator(require_POST, name='dispatch')
class UpdateCartItemView(View):
    def post(self, request, item_id):
        if not isinstance(item_id, int) or item_id < 1:
            logger.warning('Invalid item_id %s in UpdateCartItemView', item_id)
            messages.error(request, 'Invalid cart item ID.')
            return redirect('cart:cart_detail')

        try:
            cart = Cart.get_cart(request)
        except DatabaseError as e:
            logger.error('UpdateCartItemView: failed to get cart: %s', e, exc_info=True)
            messages.error(request, 'A database error occurred. Please try again.')
            return redirect('cart:cart_detail')

        try:
            item = get_object_or_404(CartItem, id=item_id, cart=cart)
        except Http404:
            logger.warning('UpdateCartItemView: item %s not found in cart %s', item_id, cart.pk)
            messages.error(request, 'Cart item not found.')
            return redirect('cart:cart_detail')

        product = item.product
        if not product.active or not product.in_stock:
            messages.error(request, f'{product.name} is no longer available.')
            try:
                item.delete()
            except DatabaseError as e:
                logger.error('UpdateCartItemView: failed to delete unavailable item %s: %s', item.pk, e, exc_info=True)
            return redirect('cart:cart_detail')

        quantity_raw = request.POST.get('quantity')
        if quantity_raw is None:
            messages.error(request, 'Quantity is required.')
            return redirect('cart:cart_detail')

        try:
            quantity = int(quantity_raw)
        except (ValueError, TypeError):
            logger.warning('UpdateCartItemView: invalid quantity value %r for item %s', quantity_raw, item_id)
            messages.error(request, 'Invalid quantity provided.')
            return redirect('cart:cart_detail')

        if quantity < 1:
            try:
                item.delete()
            except DatabaseError as e:
                logger.error('UpdateCartItemView: failed to delete item %s: %s', item.pk, e, exc_info=True)
                messages.error(request, 'Could not remove item. Please try again.')
                return redirect('cart:cart_detail')
            messages.success(request, f"{product.name} removed from cart.")
            logger.info('Removed item %s (product %s) from cart %s', item_id, product.id, cart.pk)
        elif quantity > MAX_QUANTITY_PER_ITEM:
            messages.warning(request, f'Maximum {MAX_QUANTITY_PER_ITEM} items per product.')
        elif product.stock is not None and quantity > product.stock:
            messages.warning(request, f"Only {product.stock} in stock.")
        else:
            item.quantity = quantity
            try:
                item.save()
            except DatabaseError as e:
                logger.error('UpdateCartItemView: failed to save item %s: %s', item.pk, e, exc_info=True)
                messages.error(request, 'Could not update quantity. Please try again.')
                return redirect('cart:cart_detail')
            messages.success(request, f"{product.name} quantity updated.")
            logger.info('Updated item %s quantity to %s', item_id, quantity)

        return redirect('cart:cart_detail')


@method_decorator(require_POST, name='dispatch')
class RemoveFromCartView(View):
    def post(self, request, item_id):
        if not isinstance(item_id, int) or item_id < 1:
            logger.warning('Invalid item_id %s in RemoveFromCartView', item_id)
            messages.error(request, 'Invalid cart item ID.')
            return redirect('cart:cart_detail')

        try:
            cart = Cart.get_cart(request)
        except DatabaseError as e:
            logger.error('RemoveFromCartView: failed to get cart: %s', e, exc_info=True)
            messages.error(request, 'A database error occurred. Please try again.')
            return redirect('cart:cart_detail')

        try:
            item = get_object_or_404(CartItem, id=item_id, cart=cart)
        except Http404:
            logger.warning('RemoveFromCartView: item %s not found in cart %s', item_id, cart.pk)
            messages.error(request, 'Cart item not found.')
            return redirect('cart:cart_detail')

        product_name = item.product.name
        try:
            item.delete()
        except DatabaseError as e:
            logger.error('RemoveFromCartView: failed to delete item %s: %s', item.pk, e, exc_info=True)
            messages.error(request, 'Could not remove item. Please try again.')
            return redirect('cart:cart_detail')

        messages.success(request, f"{product_name} removed from cart.")
        logger.info('Removed cart item %s (product %s)', item_id, item.product_id)
        return redirect('cart:cart_detail')


@method_decorator(require_POST, name='dispatch')
class ClearCartView(View):
    def post(self, request):
        try:
            cart = Cart.get_cart(request)
        except DatabaseError as e:
            logger.error('ClearCartView: failed to get cart: %s', e, exc_info=True)
            messages.error(request, 'A database error occurred. Please try again.')
            return redirect('cart:cart_detail')

        if not cart.items.exists():
            messages.info(request, 'Your cart is already empty.')
            return redirect('cart:cart_detail')

        try:
            cart.items.all().delete()
        except DatabaseError as e:
            logger.error('ClearCartView: failed to clear cart %s: %s', cart.pk, e, exc_info=True)
            messages.error(request, 'Could not clear cart. Please try again.')
            return redirect('cart:cart_detail')

        messages.success(request, "Cart cleared.")
        logger.info('Cleared cart %s', cart.pk)
        return redirect('cart:cart_detail')
