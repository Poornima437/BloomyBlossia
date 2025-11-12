from django.urls import path
from .import views

urlpatterns = [
    path('coupons/', views.customadmin_coupons, name='customadmin_coupons'),
    path('coupons/add/', views.customadmin_add_coupon, name='customadmin_add_coupon'),
    path('coupons/edit/<int:coupon_id>/', views.customadmin_edit_coupon, name='customadmin_edit_coupon'),
    path('coupons/toggle/<int:coupon_id>/', views.customadmin_toggle_coupon, name='customadmin_toggle_coupon'),
    path('coupons/delete/<int:coupon_id>/', views.customadmin_delete_coupon, name='customadmin_delete_coupon'),
]