from django.urls import path
from .views import CustomPasswordChangeView
from . import views

app_name = "accounts"

urlpatterns = [
    # Authentication
    path('login/', views.login_user, name='login'),
    path('signup/', views.register_user, name='signup'),
    path('logout/', views.logout_user, name='logout'),

    # OTP & Password
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('forgot-password/', views.forgot_password_request, name='forgot_password'),
    path('password-otp-verify/', views.password_otp_verify, name='password_otp_verify'),
    path('set-new-password/', views.set_new_password, name='set_new_password'),
    # path('verify-reset-otp/', views.verify_otp_and_reset, name='verify_reset_otp'),
    path('resend-reset-otp/', views.resend_reset_otp, name='resend_reset_otp'),
 
    # path('test-email/', views.test_email),


    # Profile
    path('profile/', views.user_profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.CustomPasswordChangeView.as_view(), name='change_password'),
    path('verify-email-edit/', views.verify_email_edit, name='verify_email_edit'),
    path('upload-cropped-image/', views.upload_cropped_image, name='upload_cropped_image'),
    path('send-otp/', views.send_otp_email, name='send_email_otp'),
    # path('verify-otp/', views.verify_email_otp, name='verify_email_otp'),
    path('email/otp-expire/', views.expire_email_otp, name="expire_email_otp"),
    path('profile/change-password/', CustomPasswordChangeView.as_view(), name='change_password'),


    # Address
    path('address/add/', views.add_address, name='add_address'),
    path('address/<int:pk>/edit/', views.edit_address, name='edit_address'),
    path('address/<int:pk>/delete/', views.delete_address, name='delete_address'),

   
]
