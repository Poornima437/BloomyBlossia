from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from .models import Cart, CartItem
from django.conf import settings
from django.db import transaction
from store.models import Product, Address
from store.models import ProductVariant
from django.utils import timezone
from wishlist.models import WishlistItem 
from django.http import JsonResponse
import json
from coupon.models import Coupon

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

    # shipping_cost = 100
    discount = cart.discount_amount_value()
    total = subtotal - discount

    context = {
        'items': items,
        'subtotal': subtotal,
        # 'shipping_cost': shipping_cost,
        'discount': discount,
        'total': total,
    }
    return render(request, 'user_profile/cart.html', context)



MAX_QTY = getattr(settings, "MAX_CART_QTY", 10)
MAX_ALLOWED_QTY = 5

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # PRODUCT VALIDATION
    if not product.is_active or product.is_deleted or product.status != "published":
        error_msg = "❌ This product is not available."
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": error_msg})
        messages.error(request, error_msg)
        return redirect(request.META.get("HTTP_REFERER", "cart:cart"))

    # ONLY ALLOW POST
    if request.method != "POST":
        return redirect(request.META.get("HTTP_REFERER", "cart:cart"))

    variant_id = request.POST.get("variant_id")

    # AUTO SELECT MEDIUM VARIANT IF MISSING
    if product.variants.exists() and not variant_id:
        try:
            variant_id = product.variants.get(size__iexact="Medium").id
        except ProductVariant.DoesNotExist:
            msg = "❗ Please select a size."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "message": msg})
            messages.error(request, msg)
            return redirect(request.META.get("HTTP_REFERER", "cart:cart"))

    # QUANTITY VALIDATION
    try:
        quantity = int(request.POST.get("quantity", 1))
        if quantity < 1:
            raise ValueError
    except:
        msg = "⚠ Invalid quantity."
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": msg})
        messages.error(request, msg)
        return redirect(request.META.get("HTTP_REFERER", "cart:cart"))

    MAX_ALLOWED_QTY = 5

    # GET VARIANT IF EXISTS
    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
        if variant.quantity <= 0:
            return JsonResponse({"success": False, "message": "❌ Selected size is out of stock."})

    # FETCH CART
    cart, _ = Cart.objects.get_or_create(user=request.user)

    # ADD / UPDATE ITEM
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={"quantity": quantity}
    )

    if created:  # FIRST TIME ADDING
        if quantity > MAX_ALLOWED_QTY:
            item.delete()   # ❗ REMOVE WRONG ITEM
            return JsonResponse({
                "success": False,
                "message": f"⚠ Maximum {MAX_ALLOWED_QTY} per product allowed!"
            })


    else:  # ALREADY IN CART
        if item.quantity + quantity > MAX_ALLOWED_QTY:
            return JsonResponse({
                "success": False,
                "message": f"You already have {item.quantity} in cart. Limit = {MAX_ALLOWED_QTY}."
            })
        item.quantity += quantity

    item.save()

    # REMOVE FROM WISHLIST ALWAYS
    WishlistItem.objects.filter(user=request.user, product=product).delete()

    success_msg = "🛒 Item added to cart successfully!"

    # AJAX RESPONSE
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True, "message": success_msg})

    # NORMAL REQUEST
    messages.success(request, success_msg)
    return redirect(request.META.get("HTTP_REFERER", "cart:cart"))


 

    
# @login_required
# def add_to_cart(request, product_id):
#     product = get_object_or_404(Product, id=product_id)
#     if not product.is_active or product.is_deleted or product.status != "published":
#         if request.headers.get("x-requested-with") == "XMLHttpRequest":
#             return JsonResponse({"success": False, "message": "This product is not available."})
#         messages.error(request, "This product is not available.")
#         return redirect('cart:cart')

#     if request.method != "POST":
#         return redirect(request.META.get('HTTP_REFERER', 'cart:cart'))

#     variant_id = request.POST.get('variant_id')

#     if product.variants.exists() and not variant_id:
#         try:
#             medium_variant = product.variants.get(size__iexact="Medium")
#             variant_id = medium_variant.id
#         except ProductVariant.DoesNotExist:
#             if request.headers.get("x-requested-with") == "XMLHttpRequest":
#                 return JsonResponse({"success": False, "message": "Please select a size."})
#             messages.error(request, "Please select a size.")
#             return redirect(request.META.get('HTTP_REFERER', 'cart:cart'))

#     # Validate quantity
#     try:
#         quantity = int(request.POST.get('quantity', 1))
#         if quantity < 1:
#             raise ValueError
#     except (ValueError, TypeError):
#         if request.headers.get("x-requested-with") == "XMLHttpRequest":
#             return JsonResponse({"success": False, "message": "Invalid quantity."})
#         messages.error(request, "Invalid quantity.")
#         return redirect(request.META.get('HTTP_REFERER', 'cart:cart'))

#     if variant_id:
#         variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
#         if variant.quantity <= 0:
#             return JsonResponse({"success": False, "message": "Selected size is out of stock."})
#     else:
#         variant = None

#     cart, _ = Cart.objects.get_or_create(user=request.user)
#     item, created = CartItem.objects.get_or_create(
#         cart=cart,
#         product=product,
#         variant=variant,
#         defaults={"quantity": quantity}
#     )
#     if not created:
#         item.quantity += quantity
#     item.save()

#     WishlistItem.objects.filter(user=request.user, product=product).delete()


#     if request.headers.get("x-requested-with") == "XMLHttpRequest":
#         return JsonResponse({"success": True, "message": "Item added to cart."})
#     else:
#         messages.success(request, "Item added to cart.")
#         return redirect('cart:cart')


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

            # 🚨 MAX LIMIT CHECK
            if item.quantity >= MAX_ALLOWED_QTY:
                return JsonResponse({"success": False, "message": f"Max {MAX_ALLOWED_QTY} allowed per item."})

            stock = item.variant.quantity if item.variant else item.product.quantity
            if item.quantity >= stock:
                return JsonResponse({"success": False, "message": "Not enough stock available."})

            item.quantity += 1

        elif action == "decrease":
            if item.quantity > 1:
                item.quantity -= 1
            else:
                return JsonResponse({"success": False, "message": "Quantity cannot be less than 1."})

        item.save()

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
        ) - 20

        return JsonResponse({
            "success": True,
            "quantity": item.quantity,
            "subtotal": item_subtotal,
            "total": cart_total
        })

    return JsonResponse({"success": False, "message": "Invalid request"})



# @login_required
# def update_cart_quantity(request, item_id):
#     item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
#     if request.method == "POST":
#         data = json.loads(request.body)
#         action = data.get("action")

#         if action == "increase":
#             if item.variant:
#                 stock = item.variant.quantity
#             else:
#                 stock = item.product.quantity

#             if item.quantity >= stock:
#                 return JsonResponse({"success": False, "message": "Not enough stock available."})
#             item.quantity += 1
#         elif action == "decrease":
#             if item.quantity > 1:
#                 item.quantity -= 1
#             else:
#                 return JsonResponse({"success": False, "message": "Quantity cannot be less than 1."})

#         item.save()
        
#         price = (
#             item.variant.sale_price if item.variant and item.variant.sale_price < item.variant.price else
#             item.product.sale_price if item.product.sale_price < item.product.price else
#             item.product.price
#         )
#         item_subtotal = price * item.quantity
#         cart_total = sum(
#             (
#                 i.variant.sale_price if i.variant and i.variant.sale_price < i.variant.price else
#                 i.product.sale_price if i.product.sale_price < i.product.price else
#                 i.product.price
#             ) * i.quantity for i in item.cart.items.all()
#         )+100 - 20


#         return JsonResponse({
#             "success": True,
#             "quantity": item.quantity,
#             "subtotal": item_subtotal,
#             "total": cart_total
#         })

#     return JsonResponse({"success": False, "message": "Invalid request"})


def apply_coupon(request):
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code')
        try:
            coupon = Coupon.objects.get(code__iexact=coupon_code)
            if coupon.is_valid():
                request.session['applied_coupon'] = coupon.code
                messages.success(request, f"Coupon '{coupon.code}' applied successfully!")
            else:
                messages.error(request, "Coupon expired or not active.")
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
    return redirect('cart:cart')




