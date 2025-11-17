from django import template
from wishlist.models import WishlistItem

register = template.Library()

@register.filter
def get_item(wishlist_items, product_id):
    return wishlist_items.filter(product__id=product_id).exists()
