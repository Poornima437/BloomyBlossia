from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import Order, OrderItem,Review
from django.utils import timezone
import io
from django.db import transaction
from django.db.models import F
from cart.models import CartItem, Cart
from store.models import Product, ProductVariant
from wallet.models import WalletTransaction  # optional
from django.db import transaction, models

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
        return redirect("checkout")

    user = request.user

    # Get cart
    cart = Cart.objects.filter(user=user).first()
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect("cart:view")

    cart_items = cart.items.select_related("product", "variant").all()
    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect("cart:view")

   
    variant_ids = [ci.variant.id for ci in cart_items if ci.variant]
    product_ids = [ci.product.id for ci in cart_items if not ci.variant]

    locked_variants = ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
    locked_products = Product.objects.select_for_update().filter(id__in=product_ids)

    variants_map = {v.id: v for v in locked_variants}
    products_map = {p.id: p for p in locked_products}

 
    for ci in cart_items:
        if ci.variant:
            v = variants_map[ci.variant.id]
            if v.quantity < ci.quantity:
                messages.error(request, f"Only {v.quantity} left for {v.product.name} ({v.get_size_display()})")
                return redirect("cart:view")
        else:
            p = products_map[ci.product.id]
            if p.quantity < ci.quantity:
                messages.error(request, f"Only {p.quantity} left for {p.name}")
                return redirect("cart:view")

    subtotal = sum(ci.subtotal for ci in cart_items)
    shipping_cost = 100
    discount = 0
    total = subtotal + shipping_cost - discount

   
    order = Order.objects.create(
        user=user,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        discount=discount,
        total=total,
        status="PLACED",
        created_at=timezone.now(),
    )

    for ci in cart_items:
        if ci.variant:
            v = variants_map[ci.variant.id]

            unit_price = (
                v.sale_price if v.sale_price and v.sale_price < v.price else v.price
            )

            OrderItem.objects.create(
                order=order,
                product=v.product,
                variant=v,
                quantity=ci.quantity,
                price=unit_price,
            )

            v.quantity = F("quantity") - ci.quantity
            v.save(update_fields=["quantity"])
            v.refresh_from_db()

            # UPDATE PRODUCT TOTAL STOCK
            total_stock = v.product.variants.aggregate(total=models.Sum("quantity"))["total"] or 0
            v.product.quantity = total_stock
            v.product.status = "out_of_stock" if total_stock == 0 else v.product.status
            v.product.save(update_fields=["quantity", "status"])

        else:
            p = products_map[ci.product.id]
            unit_price = p.sale_price if p.is_sale else p.price

            OrderItem.objects.create(
                order=order,
                product=p,
                variant=None,
                quantity=ci.quantity,
                price=unit_price,
            )

            p.quantity = F("quantity") - ci.quantity
            p.save(update_fields=["quantity"])
            p.refresh_from_db()
            p.status = "out_of_stock" if p.quantity == 0 else p.status
            p.save(update_fields=["status"])

   
    cart.items.all().delete()

    messages.success(request, "Order placed successfully!")
    return redirect("orders:order_success", order_id=order.order_id)


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
        action = request.POST.get('formAction')
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
                print("address_selected")

            except Address.DoesNotExist:
                messages.error(request, "Invalid address selected.")
                return redirect('orders:checkout')
            

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
                        price = (item.product.sale_price or item.product.price) * item.quantity

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
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if order.status not in ["PLACED", "PACKED"]:
        messages.error(request, "You cannot cancel this order at this stage.")
        return redirect("orders:order_detail", order_id=order.order_id)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        if len(reason) < 10:
            messages.error(request, "Please provide a cancellation reason of at least 10 characters.")
            return render(request, "user_profile/cancel_order.html", {"order": order})

        # restore stock (lock variants/products)
        variant_ids = [it.variant.id for it in order.items.all() if it.variant]
        product_ids = [it.product.id for it in order.items.all() if not it.variant]

        locked_variants = ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
        locked_products = Product.objects.select_for_update().filter(id__in=product_ids)

        # Restore quantities
        for item in order.items.select_related('product', 'variant').all():
            if item.variant:
                v = next((x for x in locked_variants if x.id == item.variant.id), None)
                if not v:
                    v = ProductVariant.objects.select_for_update().get(id=item.variant.id)
                v.quantity = F('quantity') + item.quantity
                v.save(update_fields=['quantity'])
                v.refresh_from_db()
                v.product.quantity = v.product.variants.aggregate(total=models.Sum('quantity'))['total'] or 0
                v.product.save(update_fields=['quantity', 'status'])
            else:
                p = next((x for x in locked_products if x.id == item.product.id), None)
                if not p:
                    p = Product.objects.select_for_update().get(id=item.product.id)
                p.quantity = F('quantity') + item.quantity
                p.save(update_fields=['quantity'])
                p.refresh_from_db()
                p.status = 'published' if p.quantity > 0 else p.status
                p.save(update_fields=['status'])

        # update order fields
        order.status = "CANCELED"
        order.canceled_at = timezone.now()
        order.cancel_reason = reason
        order.save()

        # Refund logic for prepaid orders
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
                messages.success(request, f"Order canceled; ₹{order.total} refunded to your wallet.")
            else:
                # Offsite refund flow (Razorpay / PayPal) — you should call their refund APIs here
                messages.success(request, "Order canceled. Refund will be processed via the original payment method.")
        else:
            messages.success(request, "Order canceled successfully.")

        return redirect("orders:orders_list")

    return render(request, "user_profile/cancel_order.html", {"order": order})

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





