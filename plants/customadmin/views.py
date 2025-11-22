from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from orders.views import restore_stock

from django.views.decorators.http import require_POST
from django.db.models import Q

from PIL import Image,UnidentifiedImageError
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.base import ContentFile
from django.contrib.auth import get_backends
# from uuid import uuid4
import uuid
from django.urls import reverse
from django.utils.safestring import mark_safe

from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.contrib.auth.models import User
from store.models import (
    Product, Category
)
from wishlist.models import WishlistItem

from orders.models import Order, OrderItem
from cart.models import Cart, CartItem
from wallet.models import WalletTransaction

from accounts.models import UserProfile
from wallet.models import Wallet
from store.forms import  ProductForm
from accounts.forms import SignUpForm,UserForm,ProfileForm,AddressForm
from store.models import Product, Category, ProductImage
from django.http import JsonResponse
import json
from django.conf import settings
from store.models import ProductVariant,VariantImage
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import F
from orders.models import ReturnRequest
from django.template.loader import get_template
from xhtml2pdf import pisa

# Create your views here.

#custom admin
def customadmin_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user:
            if user.is_staff:
                login(request, user)
                return redirect('customadmin_dashboard')
            else:
                messages.error(request, "Access denied. You are not an admin.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'custom_admin/customadmin_login.html')



@login_required
@staff_member_required
def customadmin_dashboard(request):
    if not request.user.is_staff:
        return redirect('customadmin_login')
    
    breadcrumbs = [("Dashboard", "/customadmin/dashboard/")]
    return render(request, 'custom_admin/customadmin_dashboard.html', {'breadcrumbs': breadcrumbs})

def customadmin_logout(request):
    logout(request)
    return redirect('customadmin_login')

@staff_member_required
def customadmin_products(request):
    search_query = request.GET.get('q', '')
    products = Product.objects.filter(is_deleted=False).prefetch_related('variants')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__istartswith=search_query) |
            Q(status__icontains=search_query)
        )

    products = products.order_by('-id')

    paginator = Paginator(products, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for product in page_obj:
        product.variant_list = product.variants.all()

    return render(request, 'custom_admin/products.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })

@staff_member_required
def customadmin_update_variants(request, pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=pk)
        variant_count = int(request.POST.get('variant_count', 0))
        
        for i in range(1, variant_count + 1):
            variant_id = request.POST.get(f'variant_id_{i}')
            variant_quantity = request.POST.get(f'variant_quantity_{i}')
            variant_price = request.POST.get(f'variant_price_{i}')
            variant_sale_price = request.POST.get(f'variant_sale_price_{i}')
            
            if variant_id:
                try:
                    from store.models import ProductVariant
                    variant = ProductVariant.objects.get(id=variant_id, product=product)
                    variant.quantity = int(variant_quantity)
                    variant.price = float(variant_price)
                    variant.sale_price = float(variant_sale_price)
                    variant.save()
                except ProductVariant.DoesNotExist:
                    messages.error(request, f"Variant {i} not found.")
                    continue
        
        messages.success(request, "All variants updated successfully!")
        return redirect('customadmin_edit_product', pk=product.id)
    
    return redirect('customadmin_products')

@staff_member_required
def customadmin_update_single_variant(request, variant_id):
    if request.method == 'POST':
        try:
            from store.models import ProductVariant
            import json
            
            variant = get_object_or_404(ProductVariant, id=variant_id)
            data = json.loads(request.body)
            
            variant.quantity = int(data.get('quantity', 0))
            variant.price = float(data.get('price', 0))
            variant.sale_price = float(data.get('sale_price', 0))
            variant.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Variant updated successfully',
                'data': {
                    'quantity': variant.quantity,
                    'price': variant.price,
                    'sale_price': variant.sale_price
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@staff_member_required
def toggle_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.is_blocked = not category.is_blocked
    category.save()
    return redirect('customadmin_categories') 


@staff_member_required
def customadmin_add_product(request):
    breadcrumbs = [
        ("Dashboard", "/customadmin/dashboard/"),
        ("Products", "/customadmin/products/"),
        ("Add Product", "")
    ]

    categories = Category.objects.filter(is_deleted=False)

    if request.method == 'POST':
        images = request.FILES.getlist('images')

        if len(images) < 3:
            messages.error(request, "Please upload at least 3 cropped images.")
            return render(request, 'custom_admin/customadmin_add_product.html', {
                'form': ProductForm(request.POST),
                'categories': categories,
                'breadcrumbs': breadcrumbs
            })

        mutable_post = request.POST.copy()
        mutable_files = request.FILES.copy()
        mutable_files['image'] = images[0]

        form = ProductForm(mutable_post, mutable_files)

        if form.is_valid():
            product = form.save(commit=False)

            if Product.objects.filter(name__iexact=product.name, is_deleted=False).exists():
                messages.error(request, f"Product '{product.name}' already exists.")
                return render(request, 'custom_admin/customadmin_add_product.html', {
                    'form': form,
                    'categories': categories,
                    'breadcrumbs': breadcrumbs
                })

            if product.price <= 0 or product.price > 9999.99:
                messages.error(request, "Enter a valid price between 0.01 and 9999.99.")
                return render(request, 'custom_admin/customadmin_add_product.html', {
                    'form': form,
                    'categories': categories,
                    'breadcrumbs': breadcrumbs
                })

            product.quantity = int(request.POST.get('quantity', 0))
            product.save()

            for index, image in enumerate(images):
                img = Image.open(image)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                img = img.resize((500, 500))
                thumb_io = BytesIO()
                img.save(thumb_io, format='JPEG')

                filename = f"{uuid.uuid4().hex}_{index}.jpg"
                new_image = ContentFile(thumb_io.getvalue(), name=filename)

                ProductImage.objects.create(product=product, image=new_image)

            messages.success(request, "Product added successfully!")
            return redirect('customadmin_products')
        else:
            messages.error(request, "Form is not valid. Please check the fields.")
    else:
        form = ProductForm()

    return render(request, 'custom_admin/customadmin_add_product.html', {
        'form': form,
        'categories': categories,
        'breadcrumbs': breadcrumbs
    })



@staff_member_required
def customadmin_edit_product(request, pk):
    product = get_object_or_404(Product, id=pk)
    categories = Category.objects.filter(is_deleted=False)

    if request.method == 'POST':
        name = request.POST.get('name').strip()
        try:
            original_price = float(request.POST.get('price'))
            sale_price = float(request.POST.get('sale_price'))
        except ValueError:
            messages.error(request, 'Price must be a valid number.')
            return redirect('customadmin_edit_product', pk=product.id)

        if original_price < 0 or sale_price < 0:
            messages.error(request, 'Price and Sale Price must be positive numbers.')
            return redirect('customadmin_edit_product', pk=product.id)

        if len(str(int(original_price))) > 4 or len(str(int(sale_price))) > 4:
            messages.error(request, 'Prices must be at most 4 digits before the decimal point.')
            return redirect('customadmin_edit_product', pk=product.id)

       
        if Product.objects.exclude(id=product.id).filter(name__iexact=name).exists():
            messages.error(request, 'Product with this name already exists.')
            return redirect('customadmin_edit_product', pk=product.id)

    
        product.name = name
        product.original_price = original_price
        product.sale_price = sale_price
        product.category_id = request.POST.get('category')
        product.quantity = int(request.POST.get('quantity'))
        product.status = request.POST.get('status')
        product.is_sale = 'is_sale' in request.POST
        product.save()

    
        image_files = request.FILES.getlist('images')
        if image_files:
            ProductImage.objects.filter(product=product).delete()

            for image in image_files:
                img = Image.open(image)

                if img.mode == 'RGBA':
                    img = img.convert('RGB')

                width, height = img.size
                min_dim = min(width, height)
                left = (width - min_dim) / 2
                top = (height - min_dim) / 2
                right = (width + min_dim) / 2
                bottom = (height + min_dim) / 2
                img = img.crop((left, top, right, bottom))
                img = img.resize((500, 500))

                buffer = BytesIO()
                img.save(buffer, format='JPEG')
                final_image = ContentFile(buffer.getvalue(), name=image.name)
                ProductImage.objects.create(product=product, image=final_image)

        messages.success(request, "Product updated successfully!")
        return redirect('customadmin_products')

    return render(request, 'custom_admin/customadmin_edit_product.html', {
        'product': product,
        'categories': categories
    })


@staff_member_required
def customadmin_delete_image(request, image_id):
    if request.method == 'POST':
        try:
            image = get_object_or_404(ProductImage, id=image_id)
            product = image.product
            
            current_image_count = product.images.count()
            if current_image_count <= 3:
                return JsonResponse({
                    'success': False, 
                    'message': 'Cannot delete! Product must have at least 3 images.'
                })
            
            image.delete()
            return JsonResponse({'success': True, 'message': 'Image deleted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@staff_member_required
def customadmin_delete_product(request, pk):
    product = get_object_or_404(Product, id=pk)
    product.is_deleted = True
    product.save()
    undo_url = reverse('customadmin_undo_delete_product', args=[product.id])
    messages.success(request, mark_safe(
        f"'{product.name}' deleted! <a href='{undo_url}' class='btn btn-sm btn-warning ms-3'>Undo</a>"
    ))
    return redirect('customadmin_products')

@staff_member_required
def customadmin_undo_delete_product(request, pk):
    product = get_object_or_404(Product, id=pk)
    product.is_deleted = False
    product.save()
    messages.success(request, f"'{product.name}' has been restored.")
    return redirect('customadmin_products')

@staff_member_required
def customadmin_users(request):
    search_query = request.GET.get('q', '')
    users = User.objects.all().order_by('-date_joined')
    if search_query:
        users = users.filter(username__icontains=search_query)
    paginator = Paginator(users, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'custom_admin/users.html', {'page_obj': page_obj, 'search_query': search_query})

@staff_member_required
def customadmin_block_unblock_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    return redirect('customadmin_users')

@staff_member_required
def customadmin_categories(request):
    search_query = request.GET.get('q', '')
    categories = Category.objects.filter(is_deleted=False).order_by('-created_at')

    # Block/Unblock Logic
    block_id = request.GET.get('block')
    unblock_id = request.GET.get('unblock')

    if block_id:
        category = get_object_or_404(Category, id=block_id)
        category.is_blocked = True
        category.save()
        messages.success(request, f"Category '{category.name}' has been blocked.")
        return redirect('customadmin_categories')

    if unblock_id:
        category = get_object_or_404(Category, id=unblock_id)
        category.is_blocked = False
        category.save()
        messages.success(request, f"Category '{category.name}' has been unblocked.")
        return redirect('customadmin_categories')

    if search_query:
        categories = categories.filter(name__icontains=search_query)

    paginator = Paginator(categories, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'custom_admin/categories.html', {
        'page_obj': page_obj,
        'search_query': search_query,
    })



def customadmin_add_category(request):
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            messages.error(request, "Category name cannot be empty.")
        elif Category.objects.filter(name__iexact=name, is_deleted=False).exists():
            messages.error(request, f"Category '{name}' already exists.")
        else:
            Category.objects.create(name=name, description=description)
            messages.success(request, f"Category '{name}' added successfully.")
            return redirect('customadmin_categories')

    return render(request, 'custom_admin/customadmin_add_category.html')


from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404

@staff_member_required
def customadmin_edit_category(request, pk):
    category = get_object_or_404(Category, id=pk, is_deleted=False)

    if request.method == "POST":
        new_name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not new_name:
            messages.error(request, "Category name cannot be empty.")
        elif Category.objects.exclude(id=pk).filter(name__iexact=new_name, is_deleted=False).exists():
            messages.error(request, "Category with this name already exists.")
        else:
            category.name = new_name
            category.description = description
            category.save()
            messages.success(request, "Category updated successfully.")
            return redirect('customadmin_categories')

    return render(request, 'custom_admin/customadmin_edit_category.html', {'category': category})



@staff_member_required
def customadmin_delete_category(request, pk):
    category = get_object_or_404(Category, id=pk, is_deleted=False)
    category.is_deleted = True
    category.save()
    messages.success(request, f"Category '{category.name}' has been deleted.")
    return redirect('customadmin_categories')



def customadmin_order_list(request):
    # Get search query
    search_query = request.GET.get('q', '')
    
    # Get all orders, ordered by most recent first
    orders = Order.objects.all().order_by('-created_at')
    
    # Apply search filter if query exists
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(order_id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(items__product__name__icontains=search_query)
        ).distinct()
    
    # Pagination - 10 orders per page
    paginator = Paginator(orders, 10)
    page = request.GET.get('page', 1)
    
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        orders = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        orders = paginator.page(paginator.num_pages)
    
    context = {
        'orders': orders,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/orders_list.html', context)



    
    #return render(request, 'custom_admin/orders_list.html', context)

def customadmin_order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    
    return render(request, 'custom_admin/order_detail.html', {'order': order})
@require_POST
def update_order_status(request, order_id):
    status = request.POST.get('status')
    order = get_object_or_404(Order, order_id=order_id)

    if status in dict(Order.STATUS_CHOICES).keys():
        order.status = status
        order.save()

    return redirect('customadmin_order_detail', order_id=order_id)



@login_required
@staff_member_required
def accept_return(request, order_id):

    try:
        with transaction.atomic():

            # Lock the ReturnRequest row
            rr = (
                ReturnRequest.objects
                .select_for_update()
                .get(order__order_id=order_id)
            )

            order = (
                Order.objects
                .select_for_update()
                .get(order_id=order_id)
            )

            # Validation
            if rr.status != "PENDING":
                messages.error(request, "No pending return request to accept.")
                return redirect("return_request_detail", order_id=order_id)

            # Update return request status
            rr.status = "VERIFIED"
            rr.save()

            # Restore stock for each item
            for item in order.order_items.all():
                product = Product.objects.select_for_update().get(id=item.product.id)
                product.stock += item.quantity
                product.save()

            # Update order status
            order.status = "RETURNED"
            order.save()

            # Refund money to wallet
            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            wallet.balance += order.total
            wallet.save()

        messages.success(request, "Return request accepted successfully.")
        return redirect("return_request_detail", order_id=order_id)

    except Exception as e:
        messages.error(request, f"Error accepting return: {e}")
        return redirect("return_request_detail", order_id=order_id)




@login_required
@staff_member_required
def reject_return(request, order_id):
    rr = get_object_or_404(ReturnRequest, order__order_id=order_id)

    if rr.status != "PENDING":
        messages.error(request, "No pending return request to reject.")
        return redirect("return_request_detail", order_id=order_id)

    rr.status = "REJECTED"
    rr.save()

    messages.success(request, "Return request rejected.")
    return redirect("return_request_detail", order_id=order_id)



@login_required
@staff_member_required
def return_requests(request):
    requests = ReturnRequest.objects.select_related("order", "order__user").order_by("-created_at")
    return render(request, "custom_admin/return_requests_list.html", {"requests": requests})

@login_required
@staff_member_required
def return_request_detail(request, order_id):
    rr = get_object_or_404(ReturnRequest, order__order_id=order_id)
    return render(request, "custom_admin/return_request_detail.html", {"rr": rr})



# def verify_return(request, order_id):
#     order = get_object_or_404(Order, order_id=order_id)

#     if order.return_request == 'Pending':
#         order.return_request = 'Verified'


#         wallet, _ = Wallet.objects.get_or_create(user=order.user)
#         wallet.balance += order.total
#         wallet.save()

#         order.save()

#     return redirect('customadmin_order_detail', order_id=order_id)


# @login_required
# @staff_member_required
# def accept_return(request, order_id):
#     order = get_object_or_404(Order, order_id=order_id)

#     if order.return_request != "PENDING":
#         messages.error(request, "No pending return request to accept.")
#         return redirect("customadmin_order_detail", order_id=order.order_id)


#     order.return_request = "VERIFIED"   # Accepted
#     order.status = "RETURNED"  
#     restore_stock(order)       
    
#     wallet, _ = Wallet.objects.get_or_create(user=order.user)
#     wallet.balance += order.total
#     wallet.save()
#         # add stock back
#     order.save()

#     messages.success(request, "Return request accepted.")
#     return redirect("customadmin_order_detail", order_id=order.order_id)


# @login_required
# @staff_member_required
# def reject_return(request, order_id):
#     order = get_object_or_404(Order, order_id=order_id)

#     if order.return_request != "PENDING":
#         messages.error(request, "No pending return request to reject.")
#         return redirect("customadmin_order_detail", order_id=order.order_id)


#     order.return_request = "REJECTED"
#     order.save()

#     messages.success(request, "Return request rejected.")
#     return redirect("customadmin_order_detail", order_id=order.order_id)


# def return_requests(request):
#     requests = ReturnRequest.objects.all().order_by("-created_at")
#     return render(request, "custom_admin/return_requests_list.html", {"requests": requests})


@staff_member_required
def customadmin_coupons(request):
    return render(request, 'custom_admin/coupon_list.html')


from reportlab.pdfgen import canvas

@require_POST
@staff_member_required
def reorder_product_images(request, pk):
    try:
        product = get_object_or_404(Product, id=pk)
        data = json.loads(request.body)
        order = data.get('order', [])
        for index, image_id in enumerate(order):
            image = ProductImage.objects.get(id=image_id, product=product)
            image.display_order = index  
            image.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    
def generate_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    items = order.items.all()
    return render(request, 'custom_admin/customadmin_invoice.html', {'order': order, 'items': items})


def export_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    items = order.items.all()

    template = get_template('custom_admin/customadmin_invoice.html')
    html = template.render({'order': order, 'items': items})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{order_id}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)
    return response


# def generate_invoice(request, order_id):
#     order = get_object_or_404(Order, order_id=order_id)

#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = f'inline; filename="Invoice_{order_id}.pdf"'

#     p = canvas.Canvas(response)
#     p.setFont("Helvetica-Bold", 16)
#     p.drawString(200, 800, "Invoice")

#     p.setFont("Helvetica", 12)
#     p.drawString(50, 750, f"Order ID: {order.order_id}")
#     p.drawString(50, 730, f"Customer: {order.user.get_full_name() if order.user else 'Guest'}")
#     p.drawString(50, 710, f"Email: {order.user.email if order.user else 'N/A'}")
#     p.drawString(50, 690, f"Status: {order.status}")
#     p.drawString(50, 670, f"Payment: {order.payment_method}")
#     p.drawString(50, 650, f"Total: ₹{order.total}")

#     y = 620
#     p.drawString(50, y, "Products:")
#     y -= 20
#     for item in order.items.all():
#         p.drawString(60, y, f"{item.product.name} x {item.quantity} = ₹{item.total_price}")
#         y -= 20

#     p.drawString(50, y - 10, f"Shipping Address: {order.address if order.address else 'N/A'}")

#     p.showPage()
#     p.save()
#     return response


@staff_member_required
def customadmin_add_variant_images(request, variant_id):
    if request.method == 'POST':
        variant = get_object_or_404(ProductVariant, id=variant_id)
        images = request.FILES.getlist('variant_images')
        
        if not images:
            return JsonResponse({'success': False, 'message': 'No images provided'})
        
        try:
            # Get the current highest display_order
            last_image = variant.variant_images.order_by('-display_order').first()
            start_order = (last_image.display_order + 1) if last_image else 0
            
            for index, image in enumerate(images):
                img = Image.open(image)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                # Crop to square and resize
                width, height = img.size
                min_dim = min(width, height)
                left = (width - min_dim) / 2
                top = (height - min_dim) / 2
                right = (width + min_dim) / 2
                bottom = (height + min_dim) / 2
                img = img.crop((left, top, right, bottom))
                img = img.resize((500, 500))
                
                thumb_io = BytesIO()
                img.save(thumb_io, format='JPEG')
                
                filename = f"variant_{variant.id}_{uuid.uuid4().hex}.jpg"
                new_image = ContentFile(thumb_io.getvalue(), name=filename)
                
                # Create variant image
                VariantImage.objects.create(
                    variant=variant,
                    image=new_image,
                    display_order=start_order + index
                )
            
            return JsonResponse({
                'success': True,
                'message': f'{len(images)} image(s) added successfully'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@staff_member_required
def customadmin_delete_variant_image(request, image_id):
    """Delete a specific variant image"""
    if request.method == 'POST':
        try:
            image = get_object_or_404(VariantImage, id=image_id)
            image.delete()
            return JsonResponse({'success': True, 'message': 'Image deleted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@staff_member_required
def customadmin_get_variant_images(request, variant_id):
    try:
        variant = get_object_or_404(ProductVariant, id=variant_id)
        images = variant.variant_images.all()
        
        image_data = [{
            'id': img.id,
            'url': img.image.url,
            'display_order': img.display_order
        } for img in images]
        
        return JsonResponse({
            'success': True,
            'images': image_data,
            'variant_size': variant.get_size_display(),
            'count': len(image_data)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@staff_member_required
def customadmin_reorder_variant_images(request, variant_id):
    """Reorder variant images"""
    if request.method == 'POST':
        try:
            variant = get_object_or_404(ProductVariant, id=variant_id)
            data = json.loads(request.body)
            order = data.get('order', [])
            
            for index, image_id in enumerate(order):
                image = VariantImage.objects.get(id=image_id, variant=variant)
                image.display_order = index
                image.save()
            
            return JsonResponse({'success': True, 'message': 'Images reordered successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})



