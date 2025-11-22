from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import Order, OrderItem,ReturnRequest,Review
from django.utils import timezone
import io
from django.db import transaction
from django.db.models import F,Sum
from cart.models import CartItem, Cart
from store.models import Product, ProductVariant
from wallet.models import WalletTransaction  
from django.db import transaction, models
from decimal import Decimal

from cart.models import Cart
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from store.models import Address
from .forms import CheckoutForm,CancelOrderForm, ReturnOrderForm
from django.http import JsonResponse, HttpResponseForbidden
from .models import Product


# ORDERS
@login_required
@transaction.atomic
def place_order_view(request):
    if request.method != "POST":
        return redirect("orders:checkout")

    user = request.user

    # Get cart and items
    cart = Cart.objects.filter(user=user).first()
    if not cart or not cart.items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("cart:view")

    # Always compute totals from cart items to avoid mismatches
    cart_items = cart.items.select_related("product").all()

    # Subtotal from cart items (prefer each item's stored subtotal or compute)
    # If your CartItem has a subtotal property, use that; otherwise calculate
    subtotal = sum(getattr(ci, "subtotal", None) or
                   ((ci.variant.sale_price if (ci.variant and ci.variant.sale_price and ci.variant.sale_price < ci.variant.price)
                     else (ci.product.sale_price if ci.product.is_sale else ci.product.price)) * ci.quantity)
                   for ci in cart_items)

    # Fixed shipping cost (adjust if you have dynamic shipping rules)
    shipping_cost = 50

    # If you don't apply discount here, set to 0
    discount = 0

    # Final total = cart subtotal + shipping - discount
    total = subtotal + shipping_cost - discount

    # Validate stock availability before creating order
    for ci in cart_items:
        available_qty = ci.variant.quantity if ci.variant else ci.product.quantity
        if available_qty < ci.quantity:
            name = ci.variant.product.name if ci.variant else ci.product.name
            size = f" ({ci.variant.get_size_display()})" if ci.variant else ""
            messages.error(request, f"Only {available_qty} left for {name}{size}.")
            return redirect("cart:view")

    # Create order
    order = Order.objects.create(
        user=user,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        discount=discount,
        total=total,
        status="PLACED",
        created_at=timezone.now(),
    )

    # Create order items from cart and then reduce stock centrally
    for ci in cart_items:
        # Determine unit price consistently with the subtotal calculation
        if ci.variant:
            unit_price = (ci.variant.sale_price
                          if (ci.variant.sale_price and ci.variant.sale_price < ci.variant.price)
                          else ci.variant.price)
        else:
            unit_price = (ci.product.sale_price if ci.product.is_sale else ci.product.price)

        OrderItem.objects.create(
            order=order,
            product=ci.product,
            variant=ci.variant if hasattr(ci, "variant") else None,
            quantity=ci.quantity,
            price=unit_price,
        )

    # Reduce stock for all items in one place
    reduce_stock(order)

    # Clear cart
    cart.items.all().delete()

    messages.success(request, "Order placed successfully!")
    return redirect("orders:order_success", order_id=order.order_id)




@login_required
@transaction.atomic
def checkout_view(request):
    # Get or create cart
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product')

    if not items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('cart:cart')

    # Addresses
    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    # Subtotal from cart items: use sale price if product is on sale, else regular price
    subtotal = sum(item.subtotal for item in items.all())

    # Shipping and discount
    shipping_cost = 50  # fixed shipping cost
    discount = cart.discount_amount_value()  # use your cart-level discount function
    total = subtotal + shipping_cost - discount

  

    

    if request.method == "POST":
        action = request.POST.get('formAction')

        if action == 'add_address':
            # Address validation (unchanged)
            full_name = request.POST.get('fullName', '').strip()
            phone = request.POST.get('phone', '').strip()
            address_line = request.POST.get('address', '').strip()
            city = request.POST.get('city', '').strip()
            state = request.POST.get('state', '').strip()
            zip_code = request.POST.get('zip', '').strip()
            set_as_default = request.POST.get('set_as_default') == 'on'

            errors = []
            if not full_name or len(full_name) < 3:
                errors.append("Full name must be at least 3 characters.")
            if not phone or not phone.isdigit() or len(phone) != 10 or phone[0] not in '6789':
                errors.append("Phone number must be 10 digits and start with 6, 7, 8, or 9.")
            if not address_line or len(address_line) < 5:
                errors.append("Address must be at least 5 characters.")
            if not city or len(city) < 2:
                errors.append("City name must be at least 2 characters.")
            if not state or len(state) < 2:
                errors.append("State name must be at least 2 characters.")
            if not zip_code or not zip_code.isdigit() or len(zip_code) != 6:
                errors.append("Pincode must be 6 digits.")

            if errors:
                for error in errors:
                    messages.error(request, error)
                return redirect('orders:checkout')

            if set_as_default:
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

            Address.objects.create(
                user=request.user,
                full_name=full_name,
                phone=phone,
                address_line=address_line,
                city=city,
                state=state,
                zip_code=zip_code,
                is_default=set_as_default
            )

            messages.success(request, "Address added successfully!")
            return redirect('orders:checkout')

        elif action == 'place_order':
            selected_address_id = request.POST.get('selected_address')
            payment_method = request.POST.get('payment_method')
            order_notes = request.POST.get('order_notes', '')

            if not selected_address_id or not payment_method:
                messages.error(request, "Please select address and payment method.")
                return redirect('orders:checkout')

            try:
                selected_address = Address.objects.get(
                    address_id=selected_address_id,
                    user=request.user
                )
            except Address.DoesNotExist:
                messages.error(request, "Invalid address selected.")
                return redirect('orders:checkout')

            try:
                # Validate stock for all items (products only)
                for item in items:
                    if item.product.quantity < item.quantity:
                        messages.error(request, f"Not enough stock for {item.product.name}.")
                        return redirect('orders:checkout')

                # Create order
                order = Order.objects.create(
                    user=request.user,
                    address=selected_address,
                    payment_method=payment_method,
                    subtotal=subtotal,
                    shipping_cost=shipping_cost,
                    discount=discount,
                    total=total,
                    order_notes=order_notes,
                    status="PLACED"
                )

                # Create order items (no variant)
                for item in items:
                    unit_price = (item.product.sale_price
                                  if getattr(item.product, "is_sale", False) and item.product.sale_price
                                  else item.product.price)
                    order.items.create(
                        product=item.product,
                        quantity=item.quantity,
                        price=unit_price  # unit price at purchase time
                    )

                # Reduce stock centrally
                reduce_stock(order)

                # Clear cart
                cart.items.all().delete()

                messages.success(request, "Your order has been placed successfully!")
                return redirect('orders:order_success', order_id=order.order_id)

            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
                return redirect('orders:checkout')

    context = {
        "items": items,
        "addresses": addresses,
        "default_address": default_address,
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "discount": discount,
        "total": total,
    }
    return render(request, "user_profile/checkout.html", context)




# @login_required
# def checkout_view(request):
#     # Get or create cart
#     cart, _ = Cart.objects.get_or_create(user=request.user)
#     items = cart.items.select_related('product')

#     if not items.exists():
#         messages.warning(request, "Your cart is empty.")
#         return redirect('cart:cart')  

    
#     addresses = Address.objects.filter(user=request.user)
#     default_address = addresses.filter(is_default=True).first()

#     subtotal = 0
#     for item in items:
#         item_price = item.product.sale_price if item.product.sale_price else item.product.price
#         subtotal += item_price * item.quantity

#     shipping_cost = 100
#     discount=cart.discount_amount_value()
#     total = subtotal + shipping_cost - discount

#     if request.method == "POST":
#         action = request.POST.get('formAction')
#         if action == 'add_address':
#             print("adding_address")
           
#             full_name = request.POST.get('fullName', '').strip()
#             phone = request.POST.get('phone', '').strip()
#             address_line = request.POST.get('address', '').strip()
#             city = request.POST.get('city', '').strip()
#             state = request.POST.get('state', '').strip()
#             zip_code = request.POST.get('zip', '').strip()
#             set_as_default = request.POST.get('set_as_default') == 'on'
            
#             errors = []
#             if not full_name:
#                 errors.append("Full name is required.")
#             elif len(full_name) < 3:
#                 errors.append("Full name must be at least 3 characters.")
                
#             if not phone:
#                 errors.append("Phone number is required.")
#             elif not phone.isdigit() or len(phone) != 10:
#                 errors.append("Phone number must be 10 digits.")
#             elif phone[0] not in '6789':
#                 errors.append("Phone number must start with 6, 7, 8, or 9.")
                
#             if not address_line:
#                 errors.append("Address is required.")
#             elif len(address_line) < 5:
#                 errors.append("Address must be at least 5 characters.")
                
#             if not city:
#                 errors.append("City is required.")
#             elif len(city) < 2:
#                 errors.append("City name must be at least 2 characters.")
                
#             if not state:
#                 errors.append("State is required.")
#             elif len(state) < 2:
#                 errors.append("State name must be at least 2 characters.")
                
#             if not zip_code:
#                 errors.append("Pincode is required.")
#             elif not zip_code.isdigit() or len(zip_code) != 6:
#                 errors.append("Pincode must be 6 digits.")
            
#             if errors:
#                 for error in errors:
#                     messages.error(request, error)
#                 return redirect('orders:checkout')
            
            
#             if set_as_default:
#                 Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
            
#             Address.objects.create(
#                 user=request.user,
#                 full_name=full_name,
#                 phone=phone,
#                 address_line=address_line,
#                 city=city,
#                 state=state,
#                 zip_code=zip_code,
#                 is_default=set_as_default
#             )
            
#             messages.success(request, "Address added successfully!")
#             return redirect('orders:checkout')
        
        
#         elif action == 'place_order':
#             print("adding_order")

#             selected_address_id = request.POST.get('selected_address')
#             payment_method = request.POST.get('payment_method')
#             order_notes = request.POST.get('order_notes', '')

#             if not selected_address_id:
#                 messages.error(request, "Please select a shipping address.")
#                 return redirect('orders:checkout')
            
#             if not payment_method:
#                 messages.error(request, "Please select a payment method.")
#                 return redirect('orders:checkout')
            
#             try:
#                 selected_address = Address.objects.get(address_id=selected_address_id, user=request.user)
#                 print("address_selected")

#             except Address.DoesNotExist:
#                 messages.error(request, "Invalid address selected.")
#                 return redirect('orders:checkout')
            

#             try:
#                 order = Order.objects.create(
#                     user=request.user,
#                     address=selected_address,
#                     payment_method=payment_method,
#                     subtotal=subtotal,
#                     shipping_cost=shipping_cost,
#                     discount=discount,
#                     total=total,
#                     order_notes=order_notes,
#                     status="PLACED"
#                 )
                
                
                
#                 for item in items:
#                     order_item = order.items.create(
#                         product=item.product,
#                         quantity=item.quantity,
#                         price = (item.product.sale_price or item.product.price) * item.quantity

#                     )
                
                
#                 cart.items.all().delete()
                
#                 messages.success(request, "Your order has been placed successfully!")
#                 print("success")

#                 return redirect('orders:order_success', order_id=order.order_id)
                 
            
#             except Exception as e:
#                 messages.error(request, f"An error occurred: {str(e)}")
#                 return redirect('orders:checkout')


#     context = {
#         "items": items,
#         "addresses": addresses,
#         "default_address": default_address,
#         "subtotal": subtotal,
#         "shipping_cost": shipping_cost,
#         "discount": discount,
#         "total": total,
#     }
#     return render(request, "user_profile/checkout.html", context)


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    return render(request, 'user_profile/order_success.html', {
        'order': order,
        'order_id': order.order_id
    })


@login_required
def track_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    context = {
        'order': order,
        'id': order.order_id,
        'created_at': order.created_at,
        'status': order.status,
        'items': order.items,
        'shipping_address': order.address,
    }
    
    return render(request, 'user_profile/track_order.html', context)

@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    # Fetch all order items
    items = order.items.select_related("product", "variant")

    # No calculations – only reading stored values
    context = {
        "order": order,
        "items": items,
        "subtotal": order.subtotal,
        "shipping_cost": order.shipping_cost,
        "discount": order.discount,
        "total": order.total,
    }

    return render(request, "user_profile/invoice.html", context)


# @login_required
# def download_invoice(request, order_id):
#     order = get_object_or_404(Order, order_id=order_id, user=request.user)
#     items = order.items.select_related('product')

#     subtotal = sum(item.total_price for item in items)
#     shipping_cost = order.shipping_cost
#     discount = order.discount
#     tax_rate = Decimal('0.05')
#     tax = (subtotal * tax_rate).quantize(Decimal('0.01'))  
#     total = subtotal + shipping_cost + tax - discount
    

#     context = {
#         'order': order,
#         'items': items,
#         'subtotal': subtotal,
#         'shipping_cost': shipping_cost,
#         'tax': tax,
#         'total': total,
#     }
#     return render(request, "user_profile/invoice.html", context)


@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'user_profile/order_history.html', {"orders": orders})

@login_required
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    # Only allow cancel if order is still in early stages
    if order.status not in ["PLACED", "PAID", "PACKED"]:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'You cannot cancel this order at this stage.'
            }, status=400)
        messages.error(request, "You cannot cancel this order at this stage.")
        return redirect("orders:order_detail", order_id=order.order_id)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()

        # Reason validation
        if not reason or len(reason) < 5:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Cancellation reason is required (minimum 5 characters).'
                }, status=400)
            messages.error(request, "Cancellation reason is required (minimum 5 characters).")
            return render(request, "user_profile/cancel_order.html", {"order": order})

        # Update order fields
        order.status = "CANCELED"
        order.canceled_at = timezone.now()
        order.cancel_reason = reason
        order.save()

        # Restore stock for all items
        restore_stock(order)

        # Refund logic (wallet or payment gateway)
        success_message = "Order canceled successfully."
        is_prepaid = order.payment_method in ["razorpay", "paypal"]
        is_paid = hasattr(order, "payment_status") and order.payment_status == "PAID"

        if is_prepaid and is_paid:
            if hasattr(request.user, "wallet"):
                wallet = request.user.wallet
                wallet.balance = F('balance') + order.total
                wallet.save(update_fields=['balance'])
                wallet.refresh_from_db()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type="CREDIT",
                    amount=order.total,
                    description=f"Refund for canceled order {order.order_id}",
                    order=order
                )
                success_message = f"Order canceled; ₹{order.total} refunded to your wallet."
            else:
                success_message = "Order canceled. Refund will be processed via the original payment method."

        # AJAX response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': success_message})

        # Normal response
        messages.success(request, success_message)
        return redirect("orders:orders_list")

    return render(request, "user_profile/cancel_order.html", {"order": order})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    items = order.items.select_related('product')

    context = {
        'order': order,
        'items': items,
        
    }
    return render(request, 'user_profile/order_detail.html', context)



@login_required
def orders_list(request):
    query = request.GET.get("q", "")
    orders = Order.objects.filter(user=request.user).order_by("-created_at")

    if query:
        orders = orders.filter(order_id__icontains=query)

    paginator = Paginator(orders, 10)
    page = request.GET.get('page', 1)
    
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)
    
    context = {
        'orders': orders,
        'query': query,
    }

    return render(request, "user_profile/orders_list.html", {"orders": orders, "query": query})

@login_required
@transaction.atomic
def return_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    # Only delivered orders can be returned
    if order.status != "DELIVERED":
        messages.error(request, "This order cannot be returned.")
        return redirect("orders:order_detail", order_id=order.order_id)

    # Prevent duplicate return requests
    existing_request = ReturnRequest.objects.filter(order=order).first()
    if existing_request:
        messages.info(request, "Return request already submitted for this order.")
        return redirect("orders:order_detail", order_id=order.order_id)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        if len(reason) < 5:
            messages.error(request, "Return reason must be at least 5 characters.")
            return redirect("orders:return_order", order_id=order.order_id)

        # Create the return request
        ReturnRequest.objects.create(
            order=order,
            reason=reason,
            status="PENDING"   # REQUIRED for admin
        )

        # Optionally track in order table (if needed)
        order.status = "PENDING_RETURN"
        order.save()

        messages.success(request, "Return request submitted successfully.")
        return redirect("orders:order_detail", order_id=order.order_id)

    return render(request, "user_profile/return_order.html", {"order": order})


# @login_required
# @transaction.atomic
# def return_order(request, order_id):
#     order = get_object_or_404(Order, order_id=order_id, user=request.user)

#     # Only allow return if order is returnable
#     if not order.is_returnable():
#         messages.error(request, "This order cannot be returned.")
#         return redirect("orders:order_detail", order_id=order.order_id)

#     if request.method == "POST":
#         reason = request.POST.get("reason", "").strip()
#         if not reason or len(reason) < 5:
#             messages.error(request, "Return reason is required (minimum 5 characters).")
#             return redirect("orders:return_order", order_id=order.order_id)

#         # Mark return request
#         order.return_request = "PENDING"
#         order.return_reason = reason
#         order.save()

#         messages.success(request, "Return request submitted successfully.")
#         return redirect("orders:orders_list")

#     return render(request, "user_profile/return_order.html", {"order": order})



def reduce_stock(order):
    for item in order.items.select_related('product'):
        product = Product.objects.select_for_update().get(id=item.product.id)
        product.quantity = F('quantity') - item.quantity
        product.save(update_fields=['quantity'])
        product.refresh_from_db()
        product.status = "out_of_stock" if product.quantity == 0 else "published"
        product.save(update_fields=['status'])


def restore_stock(order):
    for item in order.items.select_related('product'):
        product = Product.objects.select_for_update().get(id=item.product.id)
        product.quantity = F('quantity') + item.quantity
        product.save(update_fields=['quantity'])
        product.refresh_from_db()
        product.status = "published" if product.quantity > 0 else product.status
        product.save(update_fields=['status'])


def is_stock_available(order):
    for item in order.items.select_related('product'):
        if item.product.quantity < item.quantity:
            return False
    return True

def submit_return_request(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    # Prevent duplicate request
    if hasattr(order, 'return_request'):
        return redirect("orders:order_details", order_id=order_id)

    if request.method == "POST":
        reason = request.POST.get("reason")
        ReturnRequest.objects.create(order=order, reason=reason)
        order.status = "PENDING_RETURN"
        order.save()

        return redirect("orders:order_details", order_id=order_id)

    return render(request, "orders/return_order.html", {"order": order})
