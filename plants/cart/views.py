from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from .models import Cart, CartItem,Coupon
from django.conf import settings
from django.db import transaction
from store.models import Product, Address
from store.models import ProductVariant
from django.utils import timezone
from wishlist.models import WishlistItem 
from django.http import JsonResponse
import json

# ------------------ CART VIEWS ------------------

@login_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product','variant')
    # subtotal = sum((item.product.sale_price or item.product.price) * item.quantity for item in items)
    subtotal = 0
    for item in items:
        price = (
            item.variant.sale_price if item.variant and item.variant.sale_price < item.variant.price else
            item.product.sale_price if item.product.sale_price < item.product.price else
            item.product.price
        )
        item_subtotal = price * item.quantity
        subtotal += item_subtotal

    shipping_cost = 100
    discount = cart.discount_amount_value()
    total = subtotal + shipping_cost - discount

    context = {
        'items': items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'discount': discount,
        'total': total,
    }
    return render(request, 'user_profile/cart.html', context)



MAX_QTY = getattr(settings, "MAX_CART_QTY", 10)

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Product availability check
    if not product.is_active or product.is_deleted or product.status != "published":
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": "This product is not available."})
        messages.error(request, "This product is not available.")
        return redirect('cart:cart')

    if request.method != "POST":
        return redirect(request.META.get('HTTP_REFERER', 'cart:cart'))

    # Variant handling
    variant_id = request.POST.get('variant_id')

    # If no variant is selected and the product has variants, default to "Medium"
    if product.variants.exists() and not variant_id:
        try:
            # Try to get the "Medium" variant
            medium_variant = product.variants.get(size__iexact="Medium")
            variant_id = medium_variant.id
        except ProductVariant.DoesNotExist:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "message": "Please select a size."})
            messages.error(request, "Please select a size.")
            return redirect(request.META.get('HTTP_REFERER', 'cart:cart'))

    # Validate quantity
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1:
            raise ValueError
    except (ValueError, TypeError):
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": "Invalid quantity."})
        messages.error(request, "Invalid quantity.")
        return redirect(request.META.get('HTTP_REFERER', 'cart:cart'))

    # Get the variant if variant_id is provided
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
        if variant.quantity <= 0:
            return JsonResponse({"success": False, "message": "Selected size is out of stock."})
    else:
        variant = None

    # Add to cart
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={"quantity": quantity}
    )
    if not created:
        item.quantity += quantity
    item.save()

    # Remove from wishlist
    WishlistItem.objects.filter(user=request.user, product=product).delete()

    # Return response
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True, "message": "Item added to cart."})
    else:
        messages.success(request, "Item added to cart.")
        return redirect('cart:cart')







@login_required
def remove_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('cart:cart')


@login_required
def update_cart_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == "POST":
        data = json.loads(request.body)
        action = data.get("action")

        if action == "increase":
            if item.variant:
                stock = item.variant.quantity
            else:
                stock = item.product.quantity

            if item.quantity >= stock:
                return JsonResponse({"success": False, "message": "Not enough stock available."})
            item.quantity += 1
        elif action == "decrease":
            if item.quantity > 1:
                item.quantity -= 1
            else:
                return JsonResponse({"success": False, "message": "Quantity cannot be less than 1."})

        item.save()
    


        # Recalculate totals
        price = (
            item.variant.sale_price if item.variant and item.variant.sale_price < item.variant.price else
            item.product.sale_price if item.product.sale_price < item.product.price else
            item.product.price
        )
        item_subtotal = price * item.quantity
        cart_total = sum(
            (
                i.variant.sale_price if i.variant and i.variant.sale_price < i.variant.price else
                i.product.sale_price if i.product.sale_price < i.product.price else
                i.product.price
            ) * i.quantity for i in item.cart.items.all()
        ) + 100 - 20  


        return JsonResponse({
            "success": True,
            "quantity": item.quantity,
            "subtotal": item_subtotal,
            "total": cart_total
        })

    return JsonResponse({"success": False, "message": "Invalid request"})





# Apply Coupon
@login_required
def apply_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('coupon_code', '').strip()
        cart, _ = Cart.objects.get_or_create(user=request.user)

        if not code:
            messages.error(request, "Please enter a coupon code.")
            return redirect('cart:cart')

        try:
            coupon = Coupon.objects.get(code__iexact=code, active=True)

            # Expiry check
            if coupon.expiry_date and coupon.expiry_date < timezone.now():
                messages.error(request, "This coupon has expired.")
                return redirect('cart:cart')

            # Optional: Minimum subtotal check (say ₹500)
            if cart.total() < 500:
                messages.error(request, "This coupon is valid only on orders above ₹500.")
                return redirect('cart:cart')

            cart.coupon = coupon
            cart.save()
            messages.success(request, "Coupon applied successfully.")
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")

    return redirect('cart:cart')

