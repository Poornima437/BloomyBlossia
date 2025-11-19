
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import SignUpForm
from django.core.paginator import Paginator
import random,time
from django.conf import settings
from django.core.mail import send_mail
from orders.models import Order
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.contrib.auth.forms import PasswordChangeForm
#user profile
from accounts.forms import UserForm, ProfileForm, AddressForm
from accounts.models import UserProfile, Address

from django.contrib.auth import update_session_auth_hash
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.contrib.auth.decorators import login_required

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
import logging
from django.utils.decorators import method_decorator

# Create your views here.


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_email(email, otp, user_name=None, company_name="Bloomy Blossia"):
    subject = "Your One-Time Password (OTP) Verification"
    greeting = f"Hello {user_name}," if user_name else "Hello,"
    message = (
        f"{greeting}\n\n"
        f"We received a request to access your account. "
        f"Your One-Time Password (OTP) is:\n\n"
        f"{otp}\n\n"
        f"This OTP is valid for the next 10 minutes. "
        f"Please do not share this code with anyone.\n\n"
        f"If you did not request this, please ignore this email or contact our support team.\n\n"
        f"Thank you for trusting {company_name}.\n\n"

        f"Best regards,\n"

        f"{company_name} Team"
    )
    
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]
    
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)


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
            print("OTP Generated:", otp)
            request.session['registration_otp'] = otp
            request.session['otp_expiry'] = time.time() + 300
            request.session.save()
            
            send_mail(
                subject="Your One-Time Password (OTP) Verification",
                message=(
                    f"Dear ",
                    f"Thank you for choosing our service. To proceed with your action, please use the following One-Time Password (OTP):\n\n"
                    f"OTP: {otp}\n\n"
                    f"This OTP is valid for the next 10 minutes. Please do not share this OTP with anyone for security reasons.\n\n"
                    f"If you did not request this, please ignore this email.\n\n"
                    f"Best regards,\n"
                    f"Bloomy Blossia\n"
                    f"Support Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[form.cleaned_data['email']],
                fail_silently=False,
            )
            


          
            print(f"Generated OTP:{request.session.get('registration_otp','')}")
            return redirect('accounts:verify_otp')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})


logger = logging.getLogger(__name__)


def verify_otp(request):
    email = request.session.get('registration_data', {}).get('email', '')
    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        session_otp = request.session.get('registration_otp', '').strip()
        otp_expiry = request.session.get('otp_expiry', 0)
        current_time = time.time()

        registration_data = request.session.get('registration_data')
        if not registration_data:
            messages.error(request, "Session expired. Please register again.")
            return redirect('accounts:signup')

        if current_time > otp_expiry:
            messages.error(request, "OTP expired. Please request a new one.")
            return redirect('accounts:resend_otp')

     
        if entered_otp == session_otp:
            username = registration_data['username']
            email = registration_data['email']
            password = registration_data.get('password1') or registration_data.get('password')
            phone = registration_data.get('phone', '')

            user, created = User.objects.get_or_create(username=username, defaults={'email': email})
            if created:
                user.set_password(password)
                user.is_active = True
                user.save()

            profile, created_profile = UserProfile.objects.get_or_create(user=user)
            if created_profile and phone:
                profile.phone = phone
                profile.save()

            for key in ['registration_otp', 'otp_expiry', 'registration_data']:
                request.session.pop(key, None)

            messages.success(request, "Your account has been verified successfully! You can now log in.")
            return redirect('accounts:login')

        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return render(request, 'otp_verify.html', {'email': email})

    return render(request, 'otp_verify.html', {'email': email})


def resend_otp(request):
    
    if 'registration_data' not in request.session:
        messages.error(request, "Session expired. Please register again.")
        return redirect('accounts:signup')

    registration_data = request.session['registration_data']
    email = registration_data.get('email')

    if not email:
        messages.error(request, "Email not found in session. Please register again.")
        return redirect('accounts:signup')

    otp = str(random.randint(100000, 999999))
    request.session['registration_otp'] = otp
    request.session['otp_expiry'] = time.time() + 300 
    request.session.save()

    try:
        send_otp_email(email, otp)
        messages.success(request, f"A new OTP has been sent to {email}. Please check your inbox.")
    except Exception as e:
        messages.error(request, f"Error sending OTP: {str(e)}")

    return redirect('accounts:verify_otp')


    



def forgot_password_request(request):
    if request.method == "POST":
        email = request.POST.get("email","").strip()
        user = User.objects.filter(email=email).first()
        if user:
            otp = generate_otp()
            request.session["reset_email"] = email
            request.session["reset_otp"] = otp
            request.session['otp_expiry'] = time.time() + 300
            request.session.save()
            send_otp_email(email, otp)  
            return redirect("accounts:password_otp_verify")
        messages.error(request, "Email not found.")
    return render(request, "custom_auth/forgot_password.html")



def password_otp_verify(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        otp_session = request.session.get("reset_otp", "").strip()
        otp_expiry = request.session.get('otp_expiry', 0)
        current_time = time.time()
        logger.info(f"OTP Expiry: {otp_expiry}, Current Time: {current_time}")
        if current_time > otp_expiry:
            messages.error(request, "OTP expired. Please request a new one.")
            return redirect('accounts:resend_reset_otp')
        print(f"Entered OTP: {entered_otp}, Session OTP: {otp_session}")
        if entered_otp == otp_session:
            return redirect("accounts:set_new_password")
        else:
            messages.error(request, "Invalid OTP.")
            return render(request, "custom_auth/password_otp_verify.html", {'error': 'Invalid OTP.'})
    return render(request, "custom_auth/password_otp_verify.html")



from django.contrib.auth.hashers import make_password

def set_new_password(request):
    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("accounts:set_new_password")

        email = request.session.get("reset_email")
        if not email:
            messages.error(request, "Session expired or invalid reset link.")
            return redirect("accounts:forgot_password")

        user = User.objects.filter(email=email).first()
        if not user:
            messages.error(request, "User not found for the provided email.")
            return redirect("accounts:forgot_password")

        user.set_password(new_password)
        user.save()

        # Clean up session
        request.session.pop("reset_email", None)
        request.session.pop("reset_otp", None)

        messages.success(request, "Password updated successfully. Please log in.")
        return redirect("accounts:login")

    return render(request, "custom_auth/set_new_password.html")



def resend_reset_otp(request):
    email = request.session.get("reset_email")
    if not email:
        messages.error(request, "Session expired. Please try again.")
        return redirect("accounts:forgot_password")

    otp = generate_otp()
    print(f"Generated OTP:{request.session.get('registration_otp','')}")
    request.session["reset_otp"] = otp
    request.session["otp_expiry"] = time.time() + 300  
    request.session.save()

    send_otp_email(email, otp)
    messages.success(request, f"A new OTP has been sent to {email}. Please check your inbox.")
    return redirect("accounts:password_otp_verify")


# --------------------------------------------------------------------------------


@login_required
def user_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    default_address = Address.objects.filter(user=request.user, is_default=True).first()
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'user_profile/profile.html', {
        'user': request.user,
        'profile': profile,
        'addresses': addresses,
        'default_address': default_address,
        'orders': orders,
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
            email_changed = new_email != user.email

            # --- Email Change Handling (Optional Verification) ---
            if email_changed:
                otp = str(random.randint(100000, 999999))
                request.session['pending_email'] = new_email
                request.session['email_otp'] = otp
                request.session['otp_expired'] = False

                # Send verification email with clear instructions
                verification_message = (
                    f"Dear {user.first_name or 'User'},\n\n"
                    f"You requested to change your account email. "
                    f"Please use the OTP below to verify your new email address.\n\n"
                    f"Your OTP is: {otp}\n"
                    f"Purpose: To verify that you own the new email address before updating.\n\n"
                    f"Use this OTP within 5 minutes. If you did not request this change, "
                    f"please ignore this email.\n\n"
                    f"Thank you for using our service.\n"
                    f"Best regards,\n"
                    f"Your Company Name"
                )
                send_mail(
                    subject="OTP Verification for Email Update",
                    message=verification_message,
                    from_email="noreply@yourcompany.com",
                    recipient_list=[new_email],
                    fail_silently=False
                )

                messages.info(request, "OTP sent to new email. Please verify to complete email update.")
                return redirect('accounts:verify_email_edit')

            # --- Save user and profile if email not changed ---
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('accounts:profile')

        # --- Invalid Form Handling ---
        messages.error(request, "Please fix the errors below. They will remain visible for 5 seconds.")

    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    return render(request, 'user_profile/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

@login_required
def verify_email_edit(request):
    if 'pending_email' not in request.session:
        messages.warning(request, "No pending email change found.")
        return redirect("accounts:edit_profile")

    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        real_otp = request.session.get('email_otp')

        if not otp_entered:
            messages.error(request, "Please enter the OTP. It will remain visible for 5 seconds.")
            return redirect('accounts:verify_email_edit')

        if real_otp and otp_entered == real_otp and not request.session.get('otp_expired', False):
            user = request.user
            new_email = request.session.get('pending_email')
            user.email = new_email
            user.save()

            profile = UserProfile.objects.get(user=user)
            profile.email_verified = True
            profile.save()

            # Clear session
            for key in ['pending_email', 'email_otp', 'otp_expired']:
                request.session.pop(key, None)

            messages.success(request, "Email updated & verified successfully!")
            return redirect("accounts:profile")

        messages.error(request, "Invalid or expired OTP. Please try again. Visible for 5 seconds.")

    return render(request, "user_profile/verify_email.html")


@method_decorator(login_required, name='dispatch')
class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'user_profile/change_password.html'  # Path to your template
    success_url = reverse_lazy('accounts:profile')       # Redirect after success

    def form_valid(self, form):
        messages.success(self.request, "Password updated successfully! It will remain visible for 5 seconds.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please fix the errors below. They will remain visible for 5 seconds.")
        return super().form_invalid(form)


# @login_required
# def edit_profile(request):
#     profile = get_object_or_404(UserProfile, user=request.user)
#     user = request.user  # current user

#     if request.method == 'POST':
#         first_name = request.POST.get('first_name', user.first_name)
#         last_name = request.POST.get('last_name', user.last_name)
#         phone = request.POST.get('phone', profile.phone)
#         email = request.POST.get('email', user.email)
#         profile_image = request.FILES.get('profile_image')

#         # --- Email Verification ---
#         if email != user.email:
#             # Generate token and save in session
#             token = str(uuid.uuid4())
#             request.session['new_email'] = email
#             request.session['email_token'] = token

#             # Send verification email
#             verification_link = f"http://127.0.0.1:8000/user/profile/verify-email/{token}/"
#             send_mail(
#                 'Verify your new email',
#                 f'Click this link to verify your new email: {verification_link}',
#                 'from@example.com',
#                 [email],
#             )
#             messages.info(request, 'Verification email sent to your new email!')

#         # --- Update User fields ---
#         user.first_name = first_name
#         user.last_name = last_name
#         # Do NOT update username to avoid null errors
#         # user.username = user.username
#         user.save()

#         # --- Update Profile fields ---
#         profile.phone = phone
#         if profile_image:
#             profile.profile_image = profile_image
#         profile.save()

#         messages.success(request, 'Profile updated successfully!')
#         return redirect('accounts:profile')

#     # GET request
#     return render(request, 'user_profile/edit_profile.html', {'profile': profile ,'user': user})


# # 3. Verify Email
# @login_required
# def verify_email(request, token):
#     session_token = request.session.get('email_token')
#     new_email = request.session.get('new_email')
#     if session_token and token == session_token:
#         user = request.user
#         user.email = new_email
#         user.save()
#         profile = get_object_or_404(UserProfile, user=user)
#         profile.email_verified = True
#         profile.save()
#         # Clear session
#         del request.session['email_token']
#         del request.session['new_email']
#         messages.success(request, 'Email verified successfully!')
#     else:
#         messages.error(request, 'Invalid or expired verification link!')
#     return redirect('accounts:profile')


# from django.http import JsonResponse
# import random
# from django.core.mail import send_mail

# @login_required
# def send_email_otp(request):
#     if request.method == "POST":
#         import json
#         data = json.loads(request.body)
#         email = data.get("email")

#         if email:
#             otp = random.randint(100000, 999999)
#             print("EMAIL VERIFICATION OTP:", otp)

#             request.session['email_otp'] = str(otp)
#             request.session['email_new'] = email
#             request.session['otp_expired'] = False  # reset expiry

#             send_mail(
#                 subject="Your One-Time Password (OTP)",
#                 message=(
#                     f"Dear User,\n\n"
#                     f"Your One-Time Password (OTP) for completing your request is: {otp}\n\n"
#                     f"Please use this code within the valid time frame. "
#                     f"If you did not request this, kindly ignore this email.\n\n"
#                     f"Thank you for choosing our services.\n\n"
#                     f"Best regards,\n"
#                     f"Your Company Name"
#                 ),
#                 from_email="noreply@yourcompany.com",
#                 recipient_list=[email],
#                 fail_silently=False,
#             )

#             return JsonResponse({"success": True})

#     return JsonResponse({"success": False, "message": "Failed to send OTP."})


# @login_required
# def verify_email_otp(request):
#     if request.method == "POST":
#         import json
#         data = json.loads(request.body)

#         entered_otp = str(data.get("otp", "")).strip()

#         # Always use session values (NEVER trust frontend email)
#         session_otp = str(request.session.get("email_otp", "")).strip()
#         session_email = request.session.get("email_new")
#         expired = request.session.get("otp_expired", False)

#         # Debugging (you can remove later)
#         print("----- EMAIL OTP DEBUG -----")
#         print("Entered OTP:", entered_otp)
#         print("Session OTP:", session_otp)
#         print("Session Email:", session_email)
#         print("Expired:", expired)
#         print("----------------------------")

#         # Expired OTP
#         if expired:
#             return JsonResponse({
#                 "success": False,
#                 "message": "OTP expired. Please request a new one."
#             })

#         # OTP Match
#         if entered_otp == session_otp:
#             user = request.user
#             user.email = session_email   # Use session email ONLY
#             user.save()

#             profile = get_object_or_404(UserProfile, user=user)
#             profile.email_verified = True
#             profile.save()

#             # Clear session after success
#             request.session.pop("email_otp", None)
#             request.session.pop("email_new", None)
#             request.session.pop("otp_expired", None)

#             return JsonResponse({"success": True})

#         # Wrong OTP
#         return JsonResponse({
#             "success": False,
#             "message": "Invalid OTP. Please try again."
#         })

#     return JsonResponse({
#         "success": False,
#         "message": "Invalid request method"
#     })



# # 4. Change Password
# @login_required
# def change_password(request):
#     if request.method == 'POST':
#         form = PasswordChangeForm(user=request.user, data=request.POST)
#         if form.is_valid():
#             user = form.save()
#             update_session_auth_hash(request, user)
#             messages.success(request, 'Password changed successfully!')
#             return redirect('accounts:profile')
#         else:
#             messages.error(request, 'Please fix the errors below.')
#     else:
#         form = PasswordChangeForm(user=request.user)
#     return render(request, 'user_profile/change_password.html', {'form': form})


# 5. Cancel Orders
@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'Pending':
        order.status = 'Cancelled'
        order.save()
        messages.success(request, 'Order cancelled successfully!')
    else:
        messages.error(request, 'Cannot cancel this order!')
    return redirect('accounts:profile')

# @login_required
# def edit_profile(request):
#     user = request.user
#     profile, _ = UserProfile.objects.get_or_create(user=user)
    
#     if request.method == 'POST':
#         user_form = UserForm(request.POST, instance=user)
#         profile_form = ProfileForm(request.POST, request.FILES, instance=profile)

#         if user_form.is_valid() and profile_form.is_valid():
#             new_email = user_form.cleaned_data['email']
#             if new_email != user.email:
#                 request.session['pending_email'] = new_email
#                 otp = generate_otp()
#                 request.session['email_otp'] = otp
#                 send_otp_email(new_email, otp)
#                 return redirect('accounts:verify_email_edit')

#             user_form.save()
#             profile_form.save()
#             messages.success(request, 'Profile updated successfully.')
#             return redirect('accounts:profile')
#         else:
#             messages.error(request, " Please correct the errors and try again.")
#     else:
#         user_form = UserForm(instance=user)
#         profile_form = ProfileForm(instance=profile)

#     return render(request, 'user_profile/edit_profile.html', {
#         'user_form': user_form,
#         'profile_form': profile_form
#     })

import base64
from django.views.decorators.csrf import csrf_exempt

@login_required
@csrf_exempt
def upload_cropped_image(request):
    if request.method == "POST":
        data = request.POST.get("image")
        if not data:
            return JsonResponse({'status': 'failed', 'error': 'No image data provided'}, status=400)
        try:
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            decoded = base64.b64decode(imgstr)
            data_file = ContentFile(decoded, name=f"profile.{ext}")
            profile = get_object_or_404(UserProfile, user=request.user)
            profile.profile_image = data_file
            profile.save()
            return JsonResponse({'status': 'success'})
        except (ValueError, TypeError, base64.binascii.Error) as e:
            return JsonResponse({'status': 'failed', 'error': 'Invalid image data'}, status=400)
    return JsonResponse({'status': 'failed', 'error': 'Invalid request method'}, status=405)

@login_required
def verify_email_edit(request):
    if "pending_email" not in request.session:
        messages.warning(request, "No email update request found.")
        return redirect("accounts:edit_profile")

    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        real_otp = request.session.get('email_otp')

        if otp_entered == real_otp:
            new_email = request.session.get('pending_email')
            user = request.user
            user.email = new_email
            user.save()

          
            profile = UserProfile.objects.get(user=request.user)
            profile.email_verified = True
            profile.save()

            request.session.pop('pending_email', None)
            request.session.pop('email_otp', None)

            messages.success(request, " Email updated & Verified successfully!")
            return redirect("accounts:profile")

        messages.error(request, " Invalid OTP")

    return render(request, "user_profile/verify_email.html")
  


class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'user_profile/change_password.html'  
    success_url = reverse_lazy('accounts:profile')        

    def form_valid(self, form):
        messages.success(self.request, "Your password was updated successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)
    
@login_required
def expire_email_otp(request):
    request.session['otp_expired'] = True
    return JsonResponse({"status": "expired"})



#ADDRESS

@login_required
def dashboard_view(request):
    return render(request, 'user_profile/dashboard.html')

# @login_required
# def add_address(request):
#     if request.method == "POST":
#         form = AddressForm(request.POST)
#         if form.is_valid():
#             address = form.save(commit=False)
#             address.user = request.user
#             address.save()
#             return JsonResponse({"success": True, "message": "Address added successfully"})
#         return JsonResponse({"success": False, "errors": form.errors}, status=400)

#     # GET → Show HTML form
#     form = AddressForm()
#     return render(request, "user_profile/add_address.html", {"form": form})


@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect('accounts:profile')
    else:
        form = AddressForm()
    return render(request, 'user_profile/address.html', {'form': form})

@login_required
def edit_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    form = AddressForm(request.POST or None, instance=address)
    if form.is_valid():
        form.save()
        return redirect('accounts:profile')
    return render(request, 'user_profile/add_address.html', {'form': form})

@login_required
def delete_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.delete()
    return redirect('accounts:profile')



@login_required
def address_view(request):
    return render(request, 'user_profile/address.html')

@login_required
def user_logout(request):
    logout(request)
    return redirect('user_login')