from django.urls import path
from django.shortcuts import render, redirect, get_object_or_404
from . import views 

urlpatterns = [
    path('', lambda request: redirect('customadmin_login')),
    # Auth
    path('login/', views.customadmin_login, name='customadmin_login'),
    path('logout/', views.customadmin_logout, name='customadmin_logout'),

    # Dashboard
    path('dashboard/', views.customadmin_dashboard, name='customadmin_dashboard'),

    # Products
    path('products/', views.customadmin_products, name='customadmin_products'),
    path('products/add/', views.customadmin_add_product, name='customadmin_add_product'),
    path('products/edit/<int:pk>/', views.customadmin_edit_product, name='customadmin_edit_product'),
    path('products/delete/<int:pk>/', views.customadmin_delete_product, name='customadmin_delete_product'),
    path('products/undo/<int:pk>/', views.customadmin_undo_delete_product, name='customadmin_undo_delete_product'),
    path('products/delete-image/<int:image_id>/', views.customadmin_delete_image, name='customadmin_delete_image'),
    path('products/<int:pk>/reorder-images/', views.reorder_product_images, name='reorder_product_images'),

    # Categories
    path('categories/', views.customadmin_categories, name='customadmin_categories'),
    path('categories/add/', views.customadmin_add_category, name='customadmin_add_category'),
    path('categories/edit/<int:pk>/', views.customadmin_edit_category, name='customadmin_edit_category'),
    path('categories/delete/<int:pk>/', views.customadmin_delete_category, name='customadmin_delete_category'),
    path('categories/toggle/<int:category_id>/', views.toggle_category, name='toggle_category'),

    # Users
    path('users/', views.customadmin_users, name='customadmin_users'),
    path('users/block-unblock/<int:user_id>/', views.customadmin_block_unblock_user, name='customadmin_block_unblock_user'),

    # Orders
    path('orders/', views.customadmin_order_list, name='customadmin_order_list'),
    path('orders/<str:order_id>/', views.customadmin_order_detail, name='customadmin_order_detail'),
    path('orders/<str:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('orders/<str:order_id>/verify-return/', views.verify_return, name='verify_return'),
    path('orders/<str:order_id>/export/', views.export_invoice, name='export_invoice'),
    path('orders/<str:order_id>/generate/', views.generate_invoice, name='generate_invoice'),

    # Coupons
    path('coupons/', views.customadmin_coupons, name='customadmin_coupons'),
]
