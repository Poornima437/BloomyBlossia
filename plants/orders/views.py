from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import Order, OrderItem
from store.models import Product
from django.utils import timezone
import io
from wallet.models import WalletTransaction
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Order, OrderItem, Review
from cart.models import Cart, CartItem
from store.models import Address
from .forms import CheckoutForm,CancelOrderForm, ReturnOrderForm



@login_required
def write_review(request, order_item_id):
    order_item = get_object_or_404(OrderItem, id=order_item_id, order__user=request.user)
    existing_review = Review.objects.filter(user=request.user, order_item=order_item).first()

    if request.method == 'POST':
        rating = int(request.POST['rating'])
        feedback = request.POST['feedback']

        if existing_review:
            existing_review.rating = rating
            existing_review.feedback = feedback
            existing_review.save()
        else:
            Review.objects.create(
                user=request.user,
                order_item=order_item,
                product=order_item.product,
                rating=rating,
                feedback=feedback
            )
        return redirect('orders:order_history')

    return render(request, 'write_review.html', {
        'order_item': order_item,
        'review': existing_review
    })


@login_required
def update_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    if request.method == 'POST':
        review.rating = int(request.POST['rating'])
        review.feedback = request.POST['feedback']
        review.save()
        return redirect('orders:order_history')

    return render(request, 'write_review.html', {'review': review, 'order_item': review.order_item})


# ORDERS 

@login_required
def place_order_view(request):
    if request.method == "POST":
        user = request.user
        cart_items = CartItem.objects.filter(cart__user=user)
        if not cart_items.exists():
            return redirect('home')

        total = sum(item.product.price * item.quantity for item in cart_items)
        order = Order.objects.create(user=user, total=total, status='Pending')

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

        cart_items.delete()
        return redirect('orders:order_success', order_id=order.order_id)

    return redirect('checkout')

@login_required
def checkout_view(request):
    # Get or create cart
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product')

    if not items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('cart:cart')  

    
    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    subtotal = 0
    for item in items:
        item_price = item.product.sale_price if item.product.sale_price else item.product.price
        subtotal += item_price * item.quantity

    shipping_cost = 100
    discount=cart.discount_amount_value()
    total = subtotal + shipping_cost - discount

    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'add_address':
            print("adding_address")
           
            full_name = request.POST.get('fullName', '').strip()
            phone = request.POST.get('phone', '').strip()
            address_line = request.POST.get('address', '').strip()
            city = request.POST.get('city', '').strip()
            state = request.POST.get('state', '').strip()
            zip_code = request.POST.get('zip', '').strip()
            set_as_default = request.POST.get('set_as_default') == 'on'
            
            errors = []
            if not full_name:
                errors.append("Full name is required.")
            elif len(full_name) < 3:
                errors.append("Full name must be at least 3 characters.")
                
            if not phone:
                errors.append("Phone number is required.")
            elif not phone.isdigit() or len(phone) != 10:
                errors.append("Phone number must be 10 digits.")
            elif phone[0] not in '6789':
                errors.append("Phone number must start with 6, 7, 8, or 9.")
                
            if not address_line:
                errors.append("Address is required.")
            elif len(address_line) < 5:
                errors.append("Address must be at least 5 characters.")
                
            if not city:
                errors.append("City is required.")
            elif len(city) < 2:
                errors.append("City name must be at least 2 characters.")
                
            if not state:
                errors.append("State is required.")
            elif len(state) < 2:
                errors.append("State name must be at least 2 characters.")
                
            if not zip_code:
                errors.append("Pincode is required.")
            elif not zip_code.isdigit() or len(zip_code) != 6:
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
            print("adding_order")

            selected_address_id = request.POST.get('selected_address')
            payment_method = request.POST.get('payment_method')
            order_notes = request.POST.get('order_notes', '')

            if not selected_address_id:
                messages.error(request, "Please select a shipping address.")
                return redirect('orders:checkout')
            
            if not payment_method:
                messages.error(request, "Please select a payment method.")
                return redirect('orders:checkout')
            
            try:
                selected_address = Address.objects.get(address_id=selected_address_id, user=request.user)
                print("adress_selected")

            except Address.DoesNotExist:
                messages.error(request, "Invalid address selected.")
                return redirect('orders:checkout')
            
            print("ordd")

            try:
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
                
                
                
                for item in items:
                    order_item = order.items.create(
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.sale_price or item.product.price
                    )
                
                
                cart.items.all().delete()
                
                messages.success(request, "Your order has been placed successfully!")
                print("success")

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
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'user_profile/order_history.html', {"orders": orders})

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    # Check if order can be cancelled
    if order.status not in ["PLACED", "PACKED"]:
        messages.error(request, "You cannot cancel this order at this stage.")
        return redirect("orders:order_detail", order_id=order.order_id)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        
        # Validate reason
        if not reason or len(reason) < 10:
            messages.error(request, "Please provide a cancellation reason with at least 10 characters.")
            return render(request, "user_profile/cancel_order.html", {'order': order})
        
        # Update order status
        order.status = "CANCELED"
        order.canceled_at = timezone.now()  
        order.cancel_reason = reason
        order.save()

        # Restore stock for each item
        for item in order.items.all():
            if hasattr(item, 'variant') and item.variant:
                item.variant.stock += item.quantity
                item.variant.save()
            else:
                item.product.stock += item.quantity
                item.product.save()

        # Handle refund for prepaid orders
        if order.payment_method in ["razorpay", "paypal"] and hasattr(order, 'payment_status') and order.payment_status == "PAID":
            if hasattr(request.user, 'wallet'):
                wallet = request.user.wallet
                wallet.balance += order.total
                wallet.save()
                
                # Create wallet transaction record
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type="CREDIT",
                    amount=order.total,
                    description=f"Refund for canceled order {order.order_id}",
                    order=order
                )
                
                messages.success(
                    request, 
                    f"Order #{order.order_id} canceled successfully. ₹{order.total} has been refunded to your wallet."
                )
            else:
                messages.success(
                    request, 
                    f"Order #{order.order_id} canceled successfully. Refund will be processed within 5-7 business days."
                )
        else:
            # COD order - no refund needed
            messages.success(request, f"Order #{order.order_id} has been canceled successfully.")
        
        return redirect("orders:orders_list")

    # GET request - show cancellation form
    return render(request, "user_profile/cancel_order.html", {'order': order})
# # CANCEL ORDER 
# @login_required
# def cancel_order(request, order_id):
#     order = get_object_or_404(Order, order_id=order_id, user=request.user)
#     if order.status not in ["PLACED", "PACKED"]:
#         messages.error(request, "You cannot cancel this order at this stage.")
#         return redirect("orders:order_detail", order_id=order.order_id)

#     if request.method == "POST":
#         reason = request.POST.get("reason", "")
#         order.status = "CANCELED"
#         order.canceled_at = timezone.now()  
#         order.cancel_reason = reason
#         order.save()

#         for item in order.items.all():
#             if hasattr(item, 'variant') and item.variant:
#                 item.variant.stock += item.quantity
#                 item.variant.save()
#             else:
#                 item.product.stock += item.quantity
#                 item.product.save()

#         if order.payment_method in ["RAZORPAY", "ONLINE", "PREPAID"] and order.payment_status == "PAID":
#             # Refund to wallet
#             if hasattr(request.user, 'wallet'):
#                 wallet = request.user.wallet
#                 wallet.balance += order.total
#                 wallet.save()
                
#                 # Create wallet transaction record
#                 WalletTransaction.objects.create(
#                     wallet=wallet,
#                     transaction_type="CREDIT",
#                     amount=order.total,
#                     description=f"Refund for canceled order {order.order_id}",
#                     order=order
#                 )
                
#                 messages.success(
#                     request, 
#                     f"Order canceled successfully. ₹{order.total} has been refunded to your wallet."
#                 )
#             else:
#                 messages.success(
#                     request, 
#                     "Order canceled successfully. Refund will be processed within 5-7 business days."
#                 )
#         messages.success(request, "Order has been canceled successfully.")
#         return redirect("orders:orders_list")

#     return render(request, "user_profile/cancel_order.html", {'order':order})


@login_required
def return_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    if not order.is_returnable():
        messages.error(request, "This order cannot be returned.")
        return redirect("orders:order_detail", order_id=order.order_id)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, "Return reason is required.")
            return redirect("orders:return_order", order_id=order.order_id)

        order.return_request = "Pending"
        order.return_reason = reason
        order.save()

        messages.success(request, "Return request submitted successfully.")
        return redirect("orders:orders_list")

    return render(request, "user_profile/return_order.html", {"order": order})

@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, "user_profile/invoice.html", {"order": order})
# @login_required
# def download_invoice(request, order_id):
#     order = get_object_or_404(Order, order_id=order_id, user=request.user)

#     buffer = io.BytesIO()
#     p = canvas.Canvas(buffer, pagesize=A4)
#     width, height = A4

#     p.setFont("Helvetica-Bold", 16)
#     p.drawString(50, height - 50, f"Invoice - {order.order_id}")

#     p.setFont("Helvetica", 12)
#     p.drawString(50, height - 100, f"Customer: {order.user.username}")
#     p.drawString(50, height - 120, f"Date: {order.created_at.strftime('%Y-%m-%d')}")
#     p.drawString(50, height - 140, f"Status: {order.status}")

#     y = height - 180
#     p.drawString(50, y, "Items:")
#     y -= 20

#     for item in order.items.all():
#         p.drawString(60, y, f"{item.product.name} x {item.quantity} = Rs. {item.price * item.quantity}")
#         y -= 20

#     p.drawString(50, y - 20, f"Subtotal: Rs. {order.subtotal}")
#     p.drawString(50, y - 40, f"Shipping: Rs. {order.shipping_cost}")
#     if order.discount > 0:
#         p.drawString(50, y - 60, f"Discount: Rs. {order.discount}")
#         p.drawString(50, y - 80, f"Total Amount: Rs. {order.total}")
#     else:
#         p.drawString(50, y - 60, f"Total Amount: Rs. {order.total}")

#     p.showPage()
#     p.save()
#     buffer.seek(0)

#     response = HttpResponse(buffer, content_type="application/pdf")
#     response["Content-Disposition"] = f"attachment; filename=invoice_{order.order_id}.pdf"
#     return response


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    items = order.items.select_related('product')
    
    subtotal = sum(item.total_price for item in items)
    shipping_cost = 100
    # discount = order.discount
    total = subtotal + shipping_cost

    context = {
        'order': order,
        'items': items,
        'subtotal': subtotal,
        # 'discount': discount,
        'shipping_cost': shipping_cost,
        'total': total,
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
