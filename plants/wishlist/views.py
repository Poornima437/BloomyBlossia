from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from store.models import Product,ProductVariant
from .models import WishlistItem
from django.http import JsonResponse
from cart.models import Cart,CartItem

@login_required
def wishlist_view(request):
    wishlist_items = WishlistItem.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'user_profile/wishlist.html', {'wishlist_items': wishlist_items})



@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    size = request.POST.get('size', 'Medium')
    try:
        variant = product.variants.get(size__iexact=size)
    except ProductVariant.DoesNotExist:
        variant = None
    item, created = WishlistItem.objects.get_or_create(
        user=request.user,
        product=product,
        variant=variant
    )
    if created:
        messages.success(request, "Product added to wishlist.")
    else:
        messages.info(request, "Product already in your wishlist.")
    return redirect('wishlist:wishlist')


# @login_required
# def remove_from_wishlist(request, item_id):
#     # Safe deletion: no 404 if item doesn't exist
#     WishlistItem.objects.filter(id=item_id, user=request.user).delete()
#     messages.success(request, "Item removed from wishlist.")
#     return redirect('wishlist:wishlist')
@login_required
def remove_from_wishlist(request, item_id):
    if request.method == "POST":
        WishlistItem.objects.filter(id=item_id, user=request.user).delete()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)



# @login_required
# def toggle_wishlist(request, product_id):
#     product = get_object_or_404(Product, id=product_id)
#     wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()

#     if wishlist_item:
#         wishlist_item.delete()
#         status = "removed"
#     else:
#         Wishlist.objects.create(user=request.user, product=product)
#         status = "added"

#     return JsonResponse({"status": status})