from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from store.models import Product
from store.models import ProductVariant
from coupon.models import Coupon

# Create your models here.

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    def total(self):
        return sum(item.subtotal() for item in self.items.all())
    
    def discount_amount_value(self):
        if self.coupon:
            if self.coupon.discount_type == 'percent':
                return self.total() * (self.coupon.discount_amount / 100)
            else:  
                return self.coupon.discount_amount
        return Decimal('0.00')
    
    def final_total(self):
        subtotal = sum(item.subtotal for item in self.items.all())
        discount = self.discount_amount_value()
        shipping_cost = 100  
        total = subtotal + shipping_cost - discount
        return total if total >= 0 else Decimal('0.00')

    def __str__(self):
        return f"{self.user.username}'s Cart"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)  
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        if self.variant:
            price = self.variant.sale_price if self.variant.sale_price and self.variant.sale_price < self.variant.price else self.variant.price
        else:
            price = self.product.sale_price if self.product.sale_price and self.product.sale_price < self.product.price else self.product.price
        return price * self.quantity
    


    def __str__(self):
        name = self.variant.product.name if self.variant else self.product.name
        size = f" - {self.variant.get_size_display()}" if self.variant else ""
        return f"{name}{size} x {self.quantity}"
    


