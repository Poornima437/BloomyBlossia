from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse

from .models import Product, Category, Address
from .forms import ProductForm, AddressForm
from cart.models import Cart, CartItem
from orders.models import Order
from wishlist.models import WishlistItem

# ---------------- USER VIEWS ----------------

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

    # Category filter
    if category_id:
        try:
            products = products.filter(category__id=int(category_id))
        except ValueError:
            pass

    # Price range filter
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

    # Wishlist items
    wishlist_items = WishlistItem.objects.filter(user=request.user) if request.user.is_authenticated else WishlistItem.objects.none()

    return render(request, 'home.html', {
        'page_obj': page_obj,
        'sort_option': sort_option,
        'category_id': category_id,
        'price_range': price_range,
        'categories': categories,
        'wishlist_items': wishlist_items,
        'breadcrumbs': [("Home", "/home/")],
    })


def about(request):
    return render(request, 'about.html', {
        'breadcrumbs': [("Home", "/home/"), ("About", "/about/")]
    })


def category(request, foo):
    foo = foo.replace('-', ' ')
    try:
        Category.objects.get(name__iexact=foo)
    except Category.DoesNotExist:
        return redirect('home')
    return home(request)


# def search(request):
#     query = request.GET.get('q', '')

#     products = Product.objects.filter(name__icontains=query)

#     # AJAX Condition
#     if request.headers.get("X-Requested-With") == "XMLHttpRequest":
#         return render(request, "partials/search_results.html", {"products": products})

#     # Fallback if someone opens /search directly
#     return render(request, "search_results.html", {"products": products, "query": query})

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

    for size, price_offset in [("S", -100), ("M", 0), ("L", 100)]:
        price = max(0.01, float(product.price) + price_offset)

        if product.is_sale:
            sale_price = round(price * 0.8, 2)  # 20% OFF
        else:
            sale_price = price
        variant, created = product.variants.get_or_create(
            size=size,
            defaults={
                "price": price,
                "sale_price": sale_price,
                "quantity": product.quantity,
            },
        )
        if not created:
            variant.price = price
            variant.sale_price = sale_price
            variant.quantity = product.quantity
            variant.save()

    related_products = Product.objects.filter(
        category=product.category, is_deleted=False
    ).exclude(id=pk)[:4]

    return render(request, 'product.html', {
        'product': product,
        'related_products': related_products
    })






# ---------------- DASHBOARD ----------------

@login_required
def dashboard_view(request):
    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    total_orders = Order.objects.filter(user=request.user).count()
    pending_orders = Order.objects.filter(user=request.user, status="pending").count()
    completed_orders = Order.objects.filter(user=request.user, status="completed").count()

    context = {
        "user_name": request.user.first_name or request.user.username,
        "addresses": addresses,
        "default_address": default_address,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
    }
    return render(request, "store/dashboard.html", context)


@login_required
def address(request):
    user = request.user
    address = Address.objects.filter(user=user)

    if request.method == "POST":
        action = request.POST.get("action")  

        if action == "add":
            full_name = request.POST.get("full_name", "").strip()
            phone = request.POST.get("phone", "").strip()
            address_line = request.POST.get("address_line", "").strip()
            city = request.POST.get("city", "").strip()
            state = request.POST.get("state", "").strip()
            zip_code = request.POST.get("zip_code", "").strip()
            

            if not all([full_name, phone, address_line, city, state, zip_code]):
                messages.error(request, "All fields are required!")
                return render(request, "user_profile/address.html", {"address": address})
            elif len(phone) < 10:
                messages.error(request, "Phone number must be at least 10 digits.")
                return render(request, "user_profile/address.html", {"address": address})
            elif not zip_code.isdigit():
                messages.error(request, "ZIP code must be numeric.")
                return render(request, "user_profile/address.html", {"address": address})

            Address.objects.create(
                user=user,
                full_name=full_name,
                phone=phone,
                address_line=address_line,
                city=city,
                state=state,
                zip_code=zip_code,
            )
            
            messages.success(request, "Address added successfully!")
            print('added')
            return redirect("address")

        elif action == "delete":
            addr_id = request.POST.get("address_id")
            
            if not addr_id:
                messages.error(request, "Invalid address ID.")
                return redirect("address")
            
            try:
                address_to_delete = Address.objects.get(address_id=addr_id, user=user)
                
                # Check if address is used in any orders
                orders_with_address = Order.objects.filter(address=address_to_delete).exists()
                
                if orders_with_address:
                    messages.error(request, "Cannot delete address. It is associated with existing orders.")
                    return redirect("address")
                
                # If it's the default, reassign default to another address
                was_default = address_to_delete.is_default
                address_to_delete.delete()
                
                if was_default:
                    first_address = Address.objects.filter(user=user).first()
                    if first_address:
                        first_address.is_default = True
                        first_address.save()
                
                messages.success(request, "Address deleted successfully!")
            except Address.DoesNotExist:
                messages.error(request, "Address not found.")
            except Exception as e:
                messages.error(request, f"Error deleting address: {str(e)}")
            
            return redirect("address")

        elif action == "edit":
            try:
                address = Address.objects.get(address_id=request.POST.get("address_id"), user=user)
                is_default = request.POST.get("is_default") == "on"
                if is_default:
                    Address.objects.filter(user=user).update(is_default=False)

                address.full_name = request.POST.get("full_name", address.full_name)
                address.phone = request.POST.get("phone", address.phone)
                address.address_line = request.POST.get("address_line", address.address_line)
                address.city = request.POST.get("city", address.city)
                address.state = request.POST.get("state", address.state)
                address.zip_code = request.POST.get("zip_code", address.zip_code)
                address.is_default = is_default
                address.save()
                messages.success(request, "Address updated successfully!")
            except Address.DoesNotExist:
                messages.error(request, "Address not found.")

            return redirect("address")

    return render(request, "user_profile/address.html", {"address": address})
