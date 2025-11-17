from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from accounts.models import UserProfile, Address
from django.core.exceptions import ValidationError
import re

# Registration Form

class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        label="",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'})
    )
    username = forms.CharField(
        label="",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'User Name'})
    )
    phone = forms.CharField(
        max_length=15,
        label="",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

      
        if not re.fullmatch(r'[6-9]\d{9}', phone):
            raise ValidationError("Phone number must start with 6/7/8/9 and be 10 digits long.")

        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if not email.endswith(".com"):
            raise ValidationError("Email must end with .com")

      
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")

        return email

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)

        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'User Name'})
        self.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Email Address'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

        for field in ['username', 'email', 'password1', 'password2']:
            self.fields[field].label = ''
            self.fields[field].help_text = ''

    def save(self, commit=True):
        user = super(SignUpForm, self).save(commit=False)

        if commit:
            user.save()
            UserProfile.objects.create(user=user, phone=self.cleaned_data['phone'])

        return user



class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
           
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_image', 'phone']
        widgets = {
            'profile_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
        }



class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ['user']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'address_line': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zip Code'}),
        }
