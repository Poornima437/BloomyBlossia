from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, ProductImage
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import SignUpForm, ProductForm
from django.core.paginator import Paginator
import random,time
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import update_session_auth_hash




from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from PIL import Image,UnidentifiedImageError
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.base import ContentFile
from django.contrib.auth import get_backends
# from uuid import uuid4
import uuid


from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json
import re
#user profile
from .forms import UserForm, ProfileForm, AddressForm
from .models import UserProfile, Address
from .models import Wishlist

# review
from .models import Order, Review
#cart
from .models import Product, Cart, CartItem, Coupon
from django.db.models import F



# ============================ USER VIEWS ============================

def landing(request):
    return render(request, 'landing.html')



def home(request):
    search_query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    price_range = request.GET.get('price_range')
    sort_option = request.GET.get('sort')
    page_number = request.GET.get('page')
    categories = Category.objects.filter(is_deleted=False, is_blocked=False)
    products = Product.objects.filter(
        is_deleted=False,
        category__is_deleted=False,
        category__is_blocked=False
    )

    # Search
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Category Filter
    if category_id:
        try:
            products = products.filter(category__id=int(category_id))
        except ValueError:
            pass

    # Price Range Filter
    if price_range == '0-500':
        products = products.filter(sale_price__lte=500)
    elif price_range == '500-1000':
        products = products.filter(sale_price__gte=500, sale_price__lte=1000)
    elif price_range == '1000-2000':
        products = products.filter(sale_price__gte=1000, sale_price__lte=2000)
    elif price_range == '2000+':
        products = products.filter(sale_price__gte=2000)

    # Sorting
    if sort_option == 'price_low':
        products = products.order_by('sale_price')
    elif sort_option == 'price_high':
        products = products.order_by('-sale_price')
    elif sort_option == 'a_z':
        products = products.order_by('name')
    elif sort_option == 'z_a':
        products = products.order_by('-name')
    else:
        products = products.order_by('-id')  

    # Pagination
    paginator = Paginator(products, 8)
    page_obj = paginator.get_page(page_number)

    # Breadcrumbs
    breadcrumbs = [("Home", "/home/")]

    return render(request, 'home.html', {
        'page_obj': page_obj,
        'sort_option': sort_option,
        'category_id': category_id,
        'price_range': price_range,
        'categories': categories,
        'breadcrumbs': breadcrumbs,
    })

def about(request):
    breadcrumbs = [("Home", "/home/"), ("About", "/about/")]
    return render(request, 'about.html', {'breadcrumbs': breadcrumbs})


def category(request, foo):
    foo = foo.replace('-', ' ')
    try:
        category = Category.objects.get(name__iexact=foo)
    except Category.DoesNotExist:
        return redirect('home')
    return home(request)

def search_products(request):
    query = request.GET.get('q')
    if query:
        products = Product.objects.filter(
            Q(name__istartswith=query) | Q(category__name__icontains=query)
        ).order_by('-id')
    else:
        products = Product.objects.none()

    paginator = Paginator(products, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'search_results.html', {
        'query': query,
        'page_obj': page_obj
    })

def product(request, pk):
    product = get_object_or_404(Product, id=pk, is_deleted=False)

    
    if product.status == 'draft':
        messages.warning(request, "Product is unavailable.")
        return redirect('home')

    related_products = Product.objects.filter(
        category=product.category, is_deleted=False
    ).exclude(id=pk)[:4]

    return render(request, 'product.html', {
        'product': product,
        'related_products': related_products
    })


# def add_to_cart(request, product_id):
#     if request.method == 'POST':
#         quantity = int(request.POST.get('quantity', 1))
#         return redirect('cart')  
#  AUTH

def login_user(request):
    context = {}
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            context['login_error'] = "Both username and password are required."
            context['username'] = username
            return render(request, 'login.html', context)

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, "You have been logged in!")
            return redirect('home')
        else:
            context['username'] = username
            context['login_error'] = "Invalid username or password."

    return render(request, 'login.html', context)



def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home')

def register_user(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            request.session['registration_data'] = form.cleaned_data
            otp = str(random.randint(100000, 999999))
            request.session['registration_otp'] = otp
            print(f"Generated OTP: {otp}")
            return redirect('verify_otp')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            phone = form.cleaned_data.get('phone')
            # Save phone into the UserProfile model
            UserProfile.objects.create(user=user, phone=phone)
            return redirect('login')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})




def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        original_otp = request.session.get('registration_otp')
        email = request.session.get('registration_data', {}).get('email')

        if entered_otp == original_otp:

            data = request.session.get('registration_data')
            if data:
                User.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    password=data['password1']
                )
                messages.success(request, "Account created successfully!")
                request.session.pop('registration_data', None)
                request.session.pop('registration_otp', None)
                return redirect('login')
            else:
                messages.error(request, "Session expired. Please register again.")
                return redirect('register')

        else:
    
            return render(request, 'otp_verify.html', {
                'error': 'Invalid OTP. Please try again.',
                'email': email
            })

    email = request.session.get('registration_data', {}).get('email')
    return render(request, 'otp_verify.html', {'email': email})

def resend_otp(request):
    if 'registration_data' in request.session:
        otp = str(random.randint(100000, 999999))
        request.session['registration_otp'] = otp
        request.session['otp_failed'] = False  
        print(f"Resent OTP: {otp}")
        messages.success(request, "OTP resent successfully.")
        return redirect('verify_otp')
    else:
        messages.error(request, "Session expired. Please register again.")
        return redirect('register')



def generate_otp():
    return str(random.randint(100000, 999999))

def forgot_password_request(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()
        if user:
            otp = generate_otp()
            request.session["reset_email"] = email
            request.session["reset_otp"] = otp
            send_mail(
                "Password Reset OTP",
                f"Your OTP to reset password is {otp}",
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            return redirect("password_otp_verify")
        messages.error(request, "Email not found.")
    return render(request, "custom_auth/forgot_password.html")


def password_otp_verify(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        otp_session = request.session.get("reset_otp")
        if entered_otp == otp_session:
            return redirect("set_new_password")
        messages.error(request, "Invalid OTP.")
    return render(request, "custom_auth/password_otp_verify.html")

from django.contrib.auth.hashers import make_password


def set_new_password(request):
    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("reset_password")

        email = request.session.get("reset_email")
        if not email:
            messages.error(request, "Session expired or invalid reset link.")
            return redirect("forgot_password")

        user = User.objects.filter(email=email).first()
        if not user:
            messages.error(request, "User not found for the provided email.")
            return redirect("forgot_password")

        user.set_password(new_password)
        user.save()

        # Clean up session
        request.session.pop("reset_email", None)
        request.session.pop("reset_otp", None)

        messages.success(request, "Password updated successfully. Please log in.")
        return redirect("login")

    return render(request, "custom_auth/set_new_password.html")

def verify_otp_and_reset(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        session_otp = request.session.get("reset_otp")
        email = request.session.get("reset_email")

        if entered_otp == session_otp:
            return redirect("reset_password")
        else:
            messages.error(request, "Invalid OTP")
            return redirect("verify_reset_otp")

    return render(request, "custom_auth/verify_otp.html")
def resend_reset_otp(request):
    email = request.session.get('reset_email')
    if email:
        otp = generate_otp()
        request.session['reset_otp'] = otp

        # Send OTP email again
        send_mail(
            "Resent OTP - Password Reset",
            f"Your new OTP to reset password is: {otp}",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        messages.success(request, "OTP resent successfully!")
        return redirect('password_otp_verify')  
    else:
        messages.error(request, "Session expired or email not found.")
        return redirect('forgot_password')
    
#custom admin
def customadmin_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user:
            if user.is_staff:
                login(request, user)
                # 🔒 Skip creating/accessing userprofile for admin
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



@require_POST
@staff_member_required
def reorder_product_images(request, pk):
    try:
        product = get_object_or_404(Product, id=pk)
        data = json.loads(request.body)
        order = data.get('order', [])
        for index, image_id in enumerate(order):
            image = ProductImage.objects.get(id=image_id, product=product)
            image.display_order = index  # Make sure your ProductImage model has this field
            image.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# user profile


@login_required
def user_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'user_profile/profile.html', {
        'user': request.user,
        'profile': profile,
        'addresses': addresses
    })

@login_required
def edit_profile(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            new_email = user_form.cleaned_data['email']
            if new_email != user.email:
                request.session['pending_email'] = new_email
                otp = generate_otp()
                request.session['email_otp'] = otp
                send_email_verification(new_email, otp)
                return redirect('verify_email_edit')

            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('user_profile')
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    return render(request, 'user_profile/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

import base64
@login_required
def upload_cropped_image(request):
    if request.method == 'POST':
        image_data = request.POST.get('image')
        format, imgstr = image_data.split(';base64,')
        ext = format.split('/')[-1]
        data = ContentFile(base64.b64decode(imgstr), name=f'profile_{request.user.id}.{ext}')

        # Safely get or create the profile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.profile_picture = data
        profile.save()

        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'invalid request'}, status=400)

@login_required
def verify_email_edit(request):
    if request.method == 'POST':
        otp = request.POST.get('otp')
        if otp == request.session.get('email_otp'):
            request.user.email = request.session.get('pending_email')
            request.user.save()
            del request.session['pending_email']
            del request.session['email_otp']
            messages.success(request, 'Email updated successfully.')
            return redirect('user_profile')
        else:
            messages.error(request, 'Invalid OTP.')
    
    return render(request, 'user_profile/verify_email.html')  # NOT redirect

@login_required
def change_password(request):
    if request.method == 'POST':
        current_pwd = request.POST['current_password']
        new_pwd = request.POST['new_password']
        confirm_pwd = request.POST['confirm_password']

        if not request.user.check_password(current_pwd):
            messages.error(request, 'Incorrect current password.')
        elif new_pwd != confirm_pwd:
            messages.error(request, 'New passwords do not match.')
        else:
            request.user.set_password(new_pwd)
            request.user.save()
            update_session_auth_hash(request, request.user)  # Prevent logout
            messages.success(request, 'Password changed successfully.')
            return redirect('user_profile')

    return render(request, 'user_profile/change_password.html')


# EMAIL UTILS 

def generate_otp():
    return str(random.randint(100000, 999999))

def send_email_verification(email, otp):
    subject = 'Email Verification OTP'
    message = f'Your OTP is: {otp}'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)


#ADDRESS

@login_required
def dashboard_view(request):
    return render(request, 'user_profile/dashboard.html')

@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect('user_profile')
    else:
        form = AddressForm()
    return render(request, 'user_profile/address_form.html', {'form': form})

@login_required
def edit_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    form = AddressForm(request.POST or None, instance=address)
    if form.is_valid():
        form.save()
        return redirect('user_profile')
    return render(request, 'user_profile/address_form.html', {'form': form})

@login_required
def delete_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.delete()
    return redirect('user_profile')


# def edit_address(request, id):
    # address = get_object_or_404(Address, id=id, user=request.user)
    # if request.method == 'POST':
    #     address.full_name = request.POST['full_name']
    #     address.phone = request.POST['phone']
    #     address.address_line = request.POST['address_line']
    #     address.city = request.POST['city']
    #     address.state = request.POST['state']
    #     address.country = request.POST['country']
    #     address.zip_code = request.POST['zip_code']
    #     address.save()
    #     return redirect('profile')  # or your success page
    # return render(request, 'edit_address.html', {'address': address})


#review

@login_required
def write_review(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    existing_review = Review.objects.filter(user=request.user, order=order).first()

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
                order=order,
                rating=rating,
                feedback=feedback
            )
        return redirect('orders')

    context = {
        'order': order,
        'review': existing_review
    }
    return render(request, 'write_review.html', context)

@login_required
def update_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    if request.method == 'POST':
        review.rating = int(request.POST['rating'])
        review.feedback = request.POST['feedback']
        review.save()
        return redirect('orders')

    return render(request, 'write_review.html', {'review': review, 'order': review.order})




#cart
# Cart View
@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product')
    total = sum(item.product.sale_price * item.quantity for item in items)
    discount = cart.coupon.discount_amount if cart.coupon else 0
    final_total = total - discount

    context = {
        'items': items,
        'subtotal': total,
        'discount': discount,
        'total': final_total,
    }
    return render(request, 'user_profile/cart.html', context)

#Add to Cart
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    quantity = int(request.POST.get('quantity', 1))
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        CartItem.objects.filter(pk=item.pk).update(quantity=F('quantity') + quantity)
    else:
        item.quantity = quantity
        item.save()

    messages.success(request, "Item added to cart.")
    return redirect('cart')

#Remove Cart Item
@login_required
def remove_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('cart')

#Update Cart Quantity
@login_required
def update_cart_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

    if request.method == "POST":
        action = request.POST.get('action')  # ← FIXED: from GET to POST
        if action == 'increase':
            item.quantity += 1
        elif action == 'decrease' and item.quantity > 1:
            item.quantity -= 1
        item.save()

    return redirect('cart')

# Apply Coupon
@login_required
def apply_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        cart = Cart.objects.get(user=request.user)
        try:
            coupon = Coupon.objects.get(code=code)
            cart.coupon = coupon
            cart.save()
            messages.success(request, "Coupon applied successfully.")
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
    return redirect('cart')

# 6. Checkout
@login_required
def checkout_view(request):
    cart = Cart.objects.get(user=request.user)
    items = cart.items.all()
    if not items:
        messages.warning(request, "Your cart is empty.")
        return redirect('cart')

    total = sum(item.product.sale_price * item.quantity for item in items)  
    discount = cart.coupon.discount_amount if cart.coupon else 0  
    final_total = total - discount

    context = {
        'items': items,
        'total': final_total,
        'discount': discount,
        'subtotal': total,
    }
    return render(request, 'user_profile/checkout.html', context)

@login_required
def user_address(request):
    return render(request, 'user_profile/user_address.html')

@login_required
def track_order(request):
    order = Order.objects.filter(user=request.user).exclude(status__in=['CANCELLED', 'DELIVERED']).last()
    
    if not order:
        messages.warning(request, "No active orders found.")
        return render(request, 'user_profile/track_order.html', {'order': None})

    disallowed_statuses = ['CANCELLED', 'DELIVERED']

    return render(request, 'user_profile/track_order.html', {
        'order': order,
        'disallowed_statuses': disallowed_statuses,
    })
@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    context = {
        'wishlist_items': wishlist_items
    }
    return render(request, 'user_profile/wishlist.html', context)

@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'added'})

    return redirect('home')

@login_required
def remove_from_wishlist(request, item_id):
    wishlist_item = get_object_or_404(Wishlist, id=item_id, user=request.user)
    wishlist_item.delete()
    return redirect('wishlist')

@login_required
def address_view(request):
    return render(request, 'user_profile/address.html')

@login_required
def wallet_view(request):
    return render(request, 'user_profile/wallet.html')

@login_required
def user_logout(request):
    logout(request)
    return redirect('user_login') 
