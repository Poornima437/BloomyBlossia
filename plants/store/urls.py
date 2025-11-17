from django.urls import path
from . import views  # store views
from accounts.views import (
    login_user,
    logout_user,
    register_user,
    CustomPasswordChangeView,
    dashboard_view,
)
from wallet.views import wallet_view



urlpatterns = [
    # Public Pages
    path('', views.landing, name='landing'),
    path('home/', views.home, name='home'),
    path('about/', views.about, name='about'),

    # User Authentication
    path('login/', login_user, name='login'),
    path('logout/', logout_user, name='logout'),
    path('register/', register_user, name='register'),
    path('change-password/', CustomPasswordChangeView.as_view(), name='change_password'),

    # Shopping
    path('search/', views.search_products, name='search'),
    
    # path('search/', views.search, name='search'),

    path('product/<int:pk>/', views.product, name='product'),
    path('category/<str:foo>/', views.category, name='category'),



    # Dashboard & Wallet (from accounts)
    path('dashboard/', dashboard_view, name='dashboard'),
    path('wallet/', wallet_view, name='wallet'),
    path('address/', views.address, name='address'),

    
]
