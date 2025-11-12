from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
    path('customadmin/', include('customadmin.urls')), 
    path('accounts/', include('allauth.urls')),  # for social login
    path('user/', include('accounts.urls')),
    path('cart/', include('cart.urls')),
    path('orders/',include('orders.urls')),
    path('wishlist/',include('wishlist.urls')),
    path('wallet/',include('wallet.urls')),
    path('coupon/', include('coupon.urls')),
    
    


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
