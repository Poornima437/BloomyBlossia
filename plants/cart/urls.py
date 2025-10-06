from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_view, name='cart'),
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('update/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    
]
