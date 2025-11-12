from django.db import models
from django.utils import timezone

class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=15, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='FIXED')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2 , default=0)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    # expiry_date = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True)


    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active and
            (self.valid_from <= now) and
            (self.valid_to is None or now <= self.valid_to)
        )


    def __str__(self):
        return self.code

    def is_expired(self):
        return self.expiry_date and self.expiry_date < timezone.now()
