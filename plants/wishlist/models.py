from django.db import models
from django.contrib.auth.models import User
from store.models import Product,ProductVariant

# Create your models here.

# WISHLIST


class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product','variant')

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.variant.size if self.variant else 'No variant'})"