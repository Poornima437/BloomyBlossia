from django import forms
from .models import Product, Review
from store.models import Address
from django.contrib.auth.models import User

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



PAYMENT_CHOICES = [
    ('COD', 'Cash on Delivery'),
    ('RAZORPAY', 'Razorpay'),
    ('PAYPAL', 'PayPal'),
]

class CheckoutForm(forms.Form):
    # New Address Fields
    fullName = forms.CharField(
        max_length=100,
        required=False,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter full name',
            'id': 'fullName'
        })
    )
    
    phone = forms.CharField(
        max_length=15,
        required=False,
        label="Mobile Number",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter mobile number',
            'id': 'phone'
        })
    )
    
    address = forms.CharField(
        required=False,
        label="Address Line",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Enter address',
            'rows': 2,
            'id': 'address'
        })
    )
    
    city = forms.CharField(
        max_length=50,
        required=False,
        label="City",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter city',
            'id': 'city'
        })
    )
    
    state = forms.CharField(
        max_length=50,
        required=False,
        label="State",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter state',
            'id': 'state'
        })
    )
    
    zip = forms.CharField(
        max_length=10,
        required=False,
        label="Pincode",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter pincode',
            'id': 'zip'
        })
    )
    
    # Set as default checkbox
    set_as_default = forms.BooleanField(
        required=False,
        label="Set as default address",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'setAsDefault'
        })
    )
    
    # Payment Method
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        required=False, 
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        initial='COD'
    )
    
    selected_address = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    order_notes = forms.CharField(
        max_length=250,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Any special instructions? (optional)',
            'rows': 3
        }),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()
        action = self.data.get('action')
        
        if action == 'add_address':
            required_fields = ['fullName', 'phone', 'address', 'city', 'state', 'zip']
            errors = {}
            
            for field in required_fields:
                value = cleaned_data.get(field)
                if not value or not value.strip():
                    errors[field] = f'{field.replace("fullName", "Full Name").replace("zip", "Pincode").title()} is required.'
            
            if cleaned_data.get('phone'):
                phone = cleaned_data['phone'].strip()
                if not phone.isdigit() or len(phone) != 10:
                    errors['phone'] = 'Phone number must be 10 digits.'
                elif phone[0] not in '6789':
                    errors['phone'] = 'Phone number must start with 6, 7, 8, or 9.'
            
            if cleaned_data.get('zip'):
                zip_code = cleaned_data['zip'].strip()
                if not zip_code.isdigit() or len(zip_code) != 6:
                    errors['zip'] = 'Pincode must be 6 digits.'
            
            if errors:
                for field, error in errors.items():
                    self.add_error(field, error)
        
        elif action == 'place_order':
            if not cleaned_data.get('selected_address'):
                raise forms.ValidationError('Please select a shipping address.')
            
            if not cleaned_data.get('payment_method'):
                self.add_error('payment_method', 'Please select a payment method.')
        
        return cleaned_data

    def clean_payment_method(self):
        method = self.cleaned_data.get('payment_method')
        if method:
            valid_choices = [choice[0] for choice in PAYMENT_CHOICES]
            if method not in valid_choices:
                raise forms.ValidationError("Invalid payment method selected.")
        return method


class CancelOrderForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Please provide a reason for cancellation (optional)'
        }),
        required=False,
        label="Cancel Reason (optional)"
    )


class ReturnOrderForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Please explain why you want to return this order'
        }),
        required=True,
        label="Return Reason"
    )
    
    def clean_reason(self):
        reason = self.cleaned_data.get('reason')
        if reason and len(reason.strip()) < 10:
            raise forms.ValidationError('Please provide a detailed reason (at least 10 characters).')
        return reason


    def clean_payment_method(self):
        method = self.cleaned_data.get('payment_method')
        if method:
            valid_choices = [choice[0] for choice in PAYMENT_CHOICES]
            if method not in valid_choices:
                raise forms.ValidationError("Invalid payment method selected.")
        return method

    def clean_coupon_code(self):
        code = self.cleaned_data.get('coupon_code')
        if code:
            # Add your custom coupon validation logic here
            if len(code) < 3:
                raise forms.ValidationError("Invalid coupon code.")
        return code
    
    
class CancelOrderForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Please provide a reason for cancellation (optional)'
        }),
        required=False,
        label="Cancel Reason (optional)"
    )


class ReturnOrderForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Please explain why you want to return this order'
        }),
        required=True,
        label="Return Reason"
    )
    
    def clean_reason(self):
        reason = self.cleaned_data.get('reason')
        if reason and len(reason.strip()) < 10:
            raise forms.ValidationError('Please provide a detailed reason (at least 10 characters).')
        return reason