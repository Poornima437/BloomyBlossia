from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Product, UserProfile, Address, Review


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

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'User Name'})
        self.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Email Address'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

        # Remove help_text and labels
        for field in ['username', 'email', 'password1', 'password2']:
            self.fields[field].label = ''
            self.fields[field].help_text = ''

    def save(self, commit=True):
        user = super(SignUpForm, self).save(commit=False)
        if commit:
            user.save()
            # Create a related UserProfile instance with phone
            UserProfile.objects.create(user=user, phone=self.cleaned_data['phone'])
        return user


# Product Form
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'sale_price', 'category', 'status', 'is_sale', 'image']


# User Edit Form
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


# UserProfile Edit Form
class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_image', 'phone']


# Address Form
class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ['user']


# Review Form
class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'placeholder': 'Rating (1-5)'
        })
    )
    feedback = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'placeholder': 'Write your feedback...', 'rows': 4
        })
    )

    class Meta:
        model = Review
        fields = ['rating', 'feedback']
