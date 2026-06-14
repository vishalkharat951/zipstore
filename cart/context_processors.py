import logging

from django.core.exceptions import ObjectDoesNotExist

from .models import Cart

logger = logging.getLogger(__name__)


def cart(request):
    cart_items_count = 0
    cart_total = 0
    try:
        cart = Cart.get_cart(request)
        cart_items_count = cart.total_items
        cart_total = cart.total_price
    except ObjectDoesNotExist:
        logger.warning('Cart context processor: cart does not exist for request.')
    except AttributeError:
        logger.warning('Cart context processor: cart object missing expected attributes.')
    except TypeError as e:
        logger.warning('Cart context processor: type error computing totals: %s', e)
    except Exception as e:
        logger.error('Cart context processor: unexpected error: %s', e, exc_info=True)
    return {
        'cart_items_count': cart_items_count,
        'cart_total': cart_total,
    }
