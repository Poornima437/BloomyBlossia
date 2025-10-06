from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from store.models import Product
from store.models import ProductVariant

# Create your models here.

# CART
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    #coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)

    def total(self):
        return sum(item.subtotal() for item in self.items.all())
    
    def discount_amount_value(self):
        return self.coupon.discount_amount if self.coupon else 0
    
    def final_total(self):
        subtotal = sum(item.subtotal for item in self.items.all())
        discount = self.discount_amount_value()
        shipping_cost = 100  
        total = subtotal + shipping_cost - discount
        return total

    def __str__(self):
        return f"{self.user.username}'s Cart"


class CartItem(models.Model):
    # cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    # user = models.ForeignKey(User,on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)  # keep for migration
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        if self.variant:
            price = self.variant.price
        else:
            price = (self.product.sale_price or self.product.price)
        return price * self.quantity
    


    def __str__(self):
        name = self.variant.product.name if self.variant else self.product.name
        size = f" - {self.variant.get_size_display()}" if self.variant else ""
        return f"{name}{size} x {self.quantity}"
    


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.code