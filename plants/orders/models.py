from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

from store.models import Product, Address


# ORDER

class Order(models.Model):
    STATUS_CHOICES = [
        ("PLACED", "Placed"),
        ("PACKED", "Packed"),
        ("SHIPPED", "Shipped"),
        ("DELIVERED", "Delivered"),
        ("CANCELED", "Canceled"),
    ]

    RETURN_REQUEST_CHOICES = [
        ("None", "None"),
        ("PENDING", "Pending"),
        ("Verified", "Verified"),
        ("Rejected", "Rejected"),
    ]

    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('razorpay', 'Razorpay'),
        ('paypal', 'PayPal'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cod')
    return_request = models.CharField(max_length=10, choices=RETURN_REQUEST_CHOICES, default="None")
    cancel_reason = models.TextField(blank=True, null=True)
    canceled_at = models.DateTimeField(blank=True, null=True)
    return_reason = models.TextField(blank=True, null=True)

    order_notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PLACED")

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)


    order_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    address = models.ForeignKey(Address,on_delete=models.SET_NULL,null=True,blank=True,related_name="orders")

    def save(self, *args, **kwargs):
        if not self.order_id:
            today_str = timezone.now().strftime("%Y%m%d")
            prefix = f"ORD{today_str}"
            count = Order.objects.filter(order_id__startswith=prefix).count() + 1
            self.order_id = f"{prefix}{count:03d}"

        self.total = self.subtotal + self.shipping_cost - self.discount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_id} - {self.user.username if self.user else 'Guest'}"

    def is_returnable(self):
        return self.status == "DELIVERED" and self.return_request == "None"



class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def total_price(self):
        return self.price * self.quantity


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'order_item') 

    def __str__(self):
        return f"Review by {self.user.username} on {self.product.name}"
