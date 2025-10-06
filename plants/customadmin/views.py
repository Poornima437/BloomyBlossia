from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

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

from accounts.models import UserProfile,Wallet
from store.forms import  ProductForm
from accounts.forms import SignUpForm,UserForm,ProfileForm,AddressForm
from store.models import Product, Category, ProductImage
from django.http import JsonResponse
import json
from django.conf import settings
# Create your views here.

#custom admin
def customadmin_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user:
            if user.is_staff:
                request.session.flush()  # clear old session
                request.session.cycle_key()
                login(request, user)

                request.session.set_expiry(0) 
                request.session._session_cookie_name = getattr(settings, "ADMIN_SESSION_COOKIE_NAME", "admin_sessionid")
                return redirect('customadmin_dashboard')
            else:
                messages.error(request, "Access denied. You are not an admin.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'custom_admin/customadmin_login.html')


@login_required
def customadmin_dashboard(request):
    breadcrumbs = [("Dashboard", "/customadmin/dashboard/")]
    return render(request, 'custom_admin/customadmin_dashboard.html', {'breadcrumbs': breadcrumbs})

    if not request.user.is_staff:
        return redirect('customadmin_login')
    return render(request, 'custom_admin/customadmin_dashboard.html')

def customadmin_logout(request):
    logout(request)
    return redirect('customadmin_login')

@staff_member_required
def customadmin_products(request):
    search_query = request.GET.get('q', '')
    products = Product.objects.filter(is_deleted=False)

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(status__icontains=search_query)
        )

    products = products.order_by('-id')

    paginator = Paginator(products, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'custom_admin/products.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })

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

            # 🔒 Case-insensitive check for duplicate product name
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

        # Check for duplicate product name (excluding current product)
        if Product.objects.exclude(id=product.id).filter(name__iexact=name).exists():
            messages.error(request, 'Product with this name already exists.')
            return redirect('customadmin_edit_product', pk=product.id)

        # Update product fields
        product.name = name
        product.original_price = original_price
        product.sale_price = sale_price
        product.category_id = request.POST.get('category')
        product.quantity = int(request.POST.get('quantity'))
        product.status = request.POST.get('status')
        product.is_sale = 'is_sale' in request.POST
        product.save()

        # Handle new image uploads
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
    image = get_object_or_404(ProductImage, id=image_id)
    product_id = image.product.id
    image.delete()
    messages.success(request, "Image deleted successfully.")
    return redirect('customadmin_edit_product', pk=product_id)


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
    # search_query = request.GET.get('q', '')
    orders = Order.objects.all()

    return render(request, 'custom_admin/orders_list.html', {'orders': orders})



    
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

def verify_return(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    if order.return_request == 'Pending':
        order.return_request = 'Verified'


        wallet, _ = Wallet.objects.get_or_create(user=order.user)
        wallet.balance += order.total
        wallet.save()

        order.save()

    return redirect('customadmin_order_detail', order_id=order_id)

def customadmin_coupons(request):
    # Your code here
    return render(request, 'customadmin/coupons.html')

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
    
def export_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{order_id}.pdf"'

    p = canvas.Canvas(response)

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, "Invoice")

    # Order Info
    p.setFont("Helvetica", 12)
    p.drawString(50, 750, f"Order ID: {order.order_id}")
    p.drawString(50, 730, f"Customer: {order.user.get_full_name() if order.user else 'Guest'}")
    p.drawString(50, 710, f"Email: {order.user.email if order.user else 'N/A'}")
    p.drawString(50, 690, f"Status: {order.status}")
    p.drawString(50, 670, f"Payment: {order.payment_method}")
    p.drawString(50, 650, f"Total: ₹{order.total}")

    # Items
    y = 620
    p.drawString(50, y, "Products:")
    y -= 20
    for item in order.items.all():
        p.drawString(60, y, f"{item.product.name} x {item.quantity} = ₹{item.total_price}")
        y -= 20

    # Shipping Address
    p.drawString(50, y - 10, f"Shipping Address: {order.address if order.address else 'N/A'}")

    p.showPage()
    p.save()
    return response

def generate_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Invoice_{order_id}.pdf"'

    p = canvas.Canvas(response)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, "Invoice")

    p.setFont("Helvetica", 12)
    p.drawString(50, 750, f"Order ID: {order.order_id}")
    p.drawString(50, 730, f"Customer: {order.user.get_full_name() if order.user else 'Guest'}")
    p.drawString(50, 710, f"Email: {order.user.email if order.user else 'N/A'}")
    p.drawString(50, 690, f"Status: {order.status}")
    p.drawString(50, 670, f"Payment: {order.payment_method}")
    p.drawString(50, 650, f"Total: ₹{order.total}")

    y = 620
    p.drawString(50, y, "Products:")
    y -= 20
    for item in order.items.all():
        p.drawString(60, y, f"{item.product.name} x {item.quantity} = ₹{item.total_price}")
        y -= 20

    p.drawString(50, y - 10, f"Shipping Address: {order.address if order.address else 'N/A'}")

    p.showPage()
    p.save()
    return response