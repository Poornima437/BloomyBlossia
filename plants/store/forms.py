from django import forms
from .models import Product, Address
from accounts.models import UserProfile
from django.contrib.auth.models import User
from orders.models import Review  

# Product Form
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'sale_price', 'category', 'status', 'is_sale', 'image']

# Review Form
class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rating (1-5)'
        })
    )
    feedback = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Write your feedback...',
            'rows': 4
        })
    )

    class Meta:
        model = Review
        fields = ['rating', 'feedback']

# Address Form
class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["full_name", "phone", "address_line", "city", "state", "zip_code"]
