from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    #Public Pages
    path('', views.landing, name='landing'),
    path('home/', views.home, name='home'),
    path('about/', views.about, name='about'),

    #User Authentication
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('register/', views.register_user, name='register'),

    #OTP & Password Reset
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    #forgot password
    path('forgot-password/', views.forgot_password_request, name='forgot_password'),
    path('password-otp-verify/', views.password_otp_verify, name='password_otp_verify'),
    path('verify-reset-otp/', views.verify_otp_and_reset, name='verify_reset_otp'),
    path('resend-reset-otp/', views.resend_reset_otp, name='resend_reset_otp'),
    path('set-new-password/', views.set_new_password, name='set_new_password'),

    #Shopping
    path('search/', views.search_products, name='search'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('product/<int:pk>/', views.product, name='product'),
    path('category/<str:foo>/', views.category, name='category'),
      




    #Custom Admin Panel
    path('customadmin/', views.customadmin_login, name='customadmin_login'),
    path('customadmin/logout/', views.customadmin_logout, name='customadmin_logout'),
    path('customadmin/dashboard/', views.customadmin_dashboard, name='customadmin_dashboard'),
    path('customadmin/categories/toggle/<int:category_id>/', views.toggle_category, name='toggle_category'),


    #Product Management
    path('customadmin/products/', views.customadmin_products, name='customadmin_products'),
    path('customadmin/products/add/', views.customadmin_add_product, name='customadmin_add_product'),
    path('customadmin/products/edit/<int:pk>/', views.customadmin_edit_product, name='customadmin_edit_product'),
    path('customadmin/products/delete/<int:pk>/', views.customadmin_delete_product, name='customadmin_delete_product'),
    path('customadmin/products/undo/<int:pk>/', views.customadmin_undo_delete_product, name='customadmin_undo_delete_product'),
    path('customadmin/products/delete-image/<int:image_id>/', views.customadmin_delete_image, name='customadmin_delete_image'),
    path('customadmin/products/<int:pk>/reorder-images/', views.reorder_product_images, name='reorder_product_images'),

    #Category Management
    path('customadmin/categories/', views.customadmin_categories, name='customadmin_categories'),
    path('customadmin/categories/add/', views.customadmin_add_category, name='customadmin_add_category'),
    path('customadmin/categories/edit/<int:pk>/', views.customadmin_edit_category, name='customadmin_edit_category'),
    path('customadmin/categories/delete/<int:pk>/', views.customadmin_delete_category, name='customadmin_delete_category'),


    #User Management
    path('customadmin/users/', views.customadmin_users, name='customadmin_users'),
    path('customadmin/users/block-unblock/<int:user_id>/', views.customadmin_block_unblock_user, name='customadmin_block_unblock_user'),
#--------------------------------#
    #user profile
    path('change-password/', auth_views.PasswordChangeView.as_view(
        template_name='user/change_password.html',
        success_url='/profile/'), name='change_password'),
    path('profile/', views.user_profile, name='user_profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('verify-email-edit/', views.verify_email_edit, name='verify_email_edit'),
     path('upload-cropped-image/', views.upload_cropped_image, name='upload_cropped_image'),

    #address
    path('address/', views.user_address, name='user_address'),
    path('add-address/', views.add_address, name='add_address'),
    path('edit-address/<int:pk>/', views.edit_address, name='edit_address'),
    path('delete-address/<int:pk>/', views.delete_address, name='delete_address'),

    #cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('cart/update/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('checkout/', views.checkout_view, name='checkout'),

    # review 
    path('review/<int:order_id>/', views.write_review, name='write_review'),
    path('review/update/<int:review_id>/', views.update_review, name='update_review'),

    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('track-order/', views.track_order, name='track_order'),
    path('cart/', views.cart_view, name='shipping cart'),
    
    #wishlist

    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('address/', views.address_view, name='address'),
    path('wallet/', views.wallet_view, name='wallet'),
    path('logout/', views.user_logout, name='logout'),


]
