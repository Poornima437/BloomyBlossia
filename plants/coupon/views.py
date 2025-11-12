from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import Coupon
from django.utils.dateparse import parse_datetime

def customadmin_coupons(request):
    # Get search query
    search_query = request.GET.get('q', '')
    
    # Get all coupons, ordered by most recent first
    coupons = Coupon.objects.all().order_by('-created_at')
    
    # Apply search filter if query exists
    if search_query:
        coupons = coupons.filter(code__icontains=search_query)
    
    # Pagination - 9 coupons per page (3x3 grid)
    paginator = Paginator(coupons, 9)
    page = request.GET.get('page', 1)
    
    try:
        coupons = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        coupons = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        coupons = paginator.page(paginator.num_pages)
    
    context = {
        'coupons': coupons,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/coupons_list.html', context)


def customadmin_add_coupon(request):
    if request.method == 'POST':
        try:
            # Get form data
            code = request.POST.get('code').upper()
            discount_type = request.POST.get('discount_type')
            discount_amount = request.POST.get('discount_amount')
            min_order_value = request.POST.get('min_order_value', 0)
            max_discount = request.POST.get('max_discount', None)
            usage_limit = request.POST.get('usage_limit', None)
            valid_from = request.POST.get('valid_from')  
            valid_to = request.POST.get('valid_to')
            description = request.POST.get('description', '')
            is_active = request.POST.get('is_active') == 'on'

            valid_from = parse_datetime(valid_from) if valid_from else timezone.now()
            valid_to = parse_datetime(valid_to) if valid_to else None
            
            # Check if coupon code already exists
            if Coupon.objects.filter(code=code).exists():
                messages.error(request, 'Coupon code already exists!')
                return redirect('customadmin_add_coupon')
            
            # Create coupon
            coupon = Coupon.objects.create(
                code=code,
                discount_type=discount_type,
                discount_amount=discount_amount,
                min_order_value=min_order_value or 0,
                max_discount=max_discount if max_discount else None,
                usage_limit=usage_limit if usage_limit else None,
                valid_from=valid_from, 
                valid_to=valid_to,      
                description=description,
                is_active=is_active,
                used_count=0
            )
            
            messages.success(request, f'Coupon "{code}" created successfully!')
            return redirect('customadmin_coupons')
            
        except Exception as e:
            messages.error(request, f'Error creating coupon: {str(e)}')
            return redirect('customadmin_add_coupon')
    
    return render(request, 'custom_admin/add_coupon.html')


def customadmin_edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':
        try:
            # Update coupon data
            code = request.POST.get('code').upper()
            
            # Check if code is changed and already exists
            if code != coupon.code and Coupon.objects.filter(code=code).exists():
                messages.error(request, 'Coupon code already exists!')
                return redirect('customadmin_edit_coupon', coupon_id=coupon_id)
            
            coupon.code = code
            coupon.discount_type = request.POST.get('discount_type')
            coupon.discount_amount = request.POST.get('discount_amount')
            coupon.min_order_value = request.POST.get('min_order_value', 0)
            coupon.max_discount = request.POST.get('max_discount') or None
            coupon.usage_limit = request.POST.get('usage_limit') or None
            valid_from = request.POST.get('valid_from')
            valid_to = request.POST.get('valid_to')
            coupon.description = request.POST.get('description', '')
            coupon.is_active = request.POST.get('is_active') == 'on'

            coupon.valid_from = parse_datetime(valid_from) if valid_from else timezone.now()
            coupon.valid_to = parse_datetime(valid_to) if valid_to else None
            
            coupon.save()
            
            messages.success(request, f'Coupon "{code}" updated successfully!')
            return redirect('customadmin_coupons')
            
        except Exception as e:
            messages.error(request, f'Error updating coupon: {str(e)}')
    
    context = {
        'coupon': coupon
    }
    return render(request, 'custom_admin/edit_coupon.html', context)





def customadmin_toggle_coupon(request, coupon_id):
    """Toggle the active/inactive status of a coupon."""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.is_active = not coupon.is_active
    coupon.save()
    
    status = "activated" if coupon.is_active else "deactivated"
    messages.success(request, f'Coupon "{coupon.code}" has been {status}!')
    return redirect('customadmin_coupons')


def customadmin_delete_coupon(request, coupon_id):
    """Delete a coupon."""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    code = coupon.code
    coupon.delete()
    
    messages.success(request, f'Coupon "{code}" has been deleted!')
    return redirect('customadmin_coupons')


def validate_coupon(coupon_code, cart_total, user=None):
    """
    Validate if a coupon can be applied.
    Returns: (is_valid, discount_amount, error_message)
    """
    try:
        coupon = Coupon.objects.get(code=coupon_code.upper())
        now = timezone.now()

        # Check if active
        if not coupon.is_active:
            return False, 0, "This coupon is not active"

        # Check date validity
        if coupon.valid_from and now < coupon.valid_from:
            return False, 0, "This coupon is not yet valid"
        if coupon.valid_to and now > coupon.valid_to:
            return False, 0, "This coupon has expired"

        # Check minimum order value
        if cart_total < coupon.min_order_value:
            return False, 0, f"Minimum order value of ₹{coupon.min_order_value} required"

        # Check usage limit
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            return False, 0, "This coupon has reached its usage limit"

        # Calculate discount
        if coupon.discount_type == 'PERCENTAGE':
            discount = (cart_total * coupon.discount_amount) / 100
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
        else:  # FIXED
            discount = coupon.discount_amount

        # Ensure discount doesn't exceed total
        discount = min(discount, cart_total)
        return True, discount, ""

    except Coupon.DoesNotExist:
        return False, 0, "Invalid coupon code"
