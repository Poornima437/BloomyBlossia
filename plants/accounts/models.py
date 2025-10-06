from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


# USER PROFILE
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_image = models.ImageField(upload_to='profile/', default='default_profile.png')
    phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.user.username

    @property
    def get_profile_image(self):
        if self.profile_image:
            return self.profile_image.url
        return '/static/images/default_profile.png'


# ADDRESS
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='accounts_addresses')
    full_name = models.CharField(max_length=100, default="Unknown")
    phone = models.CharField(max_length=15, default='0000000000')
    address_line = models.CharField(max_length=255, default="To be updated")
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=10, default="000000")
    is_default = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.full_name}, {self.city}"


# WALLET
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username}'s Wallet"


# WALLET TRANSACTION
class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} of ₹{self.amount} on {self.created_at}"
