
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import SignUpForm
from django.core.paginator import Paginator
import random,time
from django.conf import settings
from django.core.mail import send_mail

from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

#user profile
from accounts.forms import UserForm, ProfileForm, AddressForm
from accounts.models import UserProfile, Address


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

# Create your views here.


def generate_otp():
    return str(random.randint(100000, 999999))

def send_email_verification(email, otp):
    subject = 'Your New OTP for Signup'
    message = f'Your new OTP is: {otp}. It is valid for 5 minutes.'
    from_email = settings.DEFAULT_FROM_EMAIL
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
            request.session['registration_otp'] = otp
            request.session['otp_expiry'] = time.time() + 300
            request.session.save()
            print(f"Generated OTP:89 {request.session.get('registration_otp','')}")
            return redirect('accounts:verify_otp')
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


import logging
logger = logging.getLogger(__name__)

def verify_otp(request):
    email = request.session.get('registration_data', {}).get('email', '')
    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        original_otp = request.session.get('registration_otp', '000000').strip()
        print(original_otp)
        otp_expiry = request.session.get('otp_expiry', 0)
        current_time = time.time()

        if current_time > otp_expiry:
            messages.error(request, "OTP expired. Please request a new one.")
            return redirect('resend_otp')

        if entered_otp == original_otp:
            data = request.session.get('registration_data')
            if data:
                print("Original password (for debug only):", data['password1'])
                User.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    password=data['password1']
                )
                messages.success(request, "Account created successfully!")
                request.session.pop('registration_data', None)
                request.session.pop('registration_otp', None)
                request.session.pop('otp_expiry', None)
                return redirect('login')
            else:
                messages.error(request, "Session expired. Please register again.")
                return redirect('register')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return render(request, 'otp_verify.html', {'email': email})

    return render(request, 'otp_verify.html', {'email': email})



def resend_otp(request):
    if 'registration_data' in request.session:
        # Clear old OTP
        request.session.pop('registration_otp', None)
        request.session.pop('otp_expiry', None)

        # Generate new OTP
        otp = str(random.randint(100000, 999999))
        request.session['registration_otp'] = otp
        request.session['otp_expiry'] = time.time() + 300
        request.session.save()

        # Send new OTP to user's email
        email = request.session['registration_data']['email']
        send_email_verification(email, otp)

        messages.success(request, "A new OTP has been sent to your email.")
        return redirect('verify_otp')
    else:
        messages.error(request, "Session expired. Please register again.")
        return redirect('register')
    



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
            send_email_verification(email, otp)  # <-- Replace send_mail with this line
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
            return redirect("accounts:reset_password")

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

def verify_otp_and_reset(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        session_otp = request.session.get("reset_otp")
        email = request.session.get("reset_email")

        if entered_otp == session_otp:
            return redirect("accounts:reset_password")
        else:
            messages.error(request, "Invalid OTP")
            return redirect("accounts:verify_reset_otp")

    return render(request, "custom_auth/verify_otp.html")
    
def resend_reset_otp(request):
    email = request.session.get("reset_email")
    if not email:
        messages.error(request, "Session expired. Please try again.")
        return redirect("accounts:forgot_password")
    otp = generate_otp()
    request.session["reset_otp"] = otp
    request.session['otp_expiry'] = time.time() + 300
    request.session.save()
    send_email_verification(email, otp)  # <-- Replace send_mail with this line
    messages.success(request, "A new OTP has been sent to your email.")
    return redirect("accounts:password_otp_verify")

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
                return redirect('accounts:verify_email_edit')

            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
        else:
            messages.error(request, " Please correct the errors and try again.")
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
    if request.method == "POST":
        data = request.POST.get("image")  
        format, imgstr = data.split(';base64,')
        ext = format.split('/')[-1]
        data = ContentFile(base64.b64decode(imgstr), name=f"profile.{ext}")

        profile = get_object_or_404(UserProfile, user=request.user)
        profile.profile_image = data
        profile.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})

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
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Invalid OTP.')
    
    return render(request, 'user_profile/verify_email.html')  # NOT redirect


class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'user_profile/change_password.html'  
    success_url = reverse_lazy('accounts:profile')        

    def form_valid(self, form):
        messages.success(self.request, "Your password was updated successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    
# EMAIL UTILS 



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
            return redirect('accounts:profile')
    else:
        form = AddressForm()
    return render(request, 'user_profile/address_form.html', {'form': form})

@login_required
def edit_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    form = AddressForm(request.POST or None, instance=address)
    if form.is_valid():
        form.save()
        return redirect('accounts:profile')
    return render(request, 'user_profile/address_form.html', {'form': form})

@login_required
def delete_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.delete()
    return redirect('accounts:profile')




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