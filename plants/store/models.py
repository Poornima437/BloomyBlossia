from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import models
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from cloudinary.models import CloudinaryField
# CATEGORY

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_deleted = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


# PRODUCT

class Product(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    image = CloudinaryField('image', folder='products')
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    sale_price = models.DecimalField(
        default=0, decimal_places=2, max_digits=8
    )  # Discount price if applicable
    is_sale = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=1)

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("out_of_stock", "Out of Stock"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    def save(self, *args, **kwargs):
        creating = self.pk is None  

        if self.quantity == 0:
            self.status = "out_of_stock"
        elif self.status == "out_of_stock" and self.quantity > 0:
            self.status = "published"

        if self.is_sale:
            self.sale_price = round(self.price * Decimal("0.8"), 2)
        else:
            self.sale_price = self.price

        super().save(*args, **kwargs)

        if not creating:
            for size, price_offset in [("S", -100), ("M", 0), ("L", 100)]:
                price = max(0.01, float(self.price) + price_offset)
                sale_price = max(0.01, float(self.sale_price) + price_offset)

                try:
                    with transaction.atomic():
                        variant, created = self.variants.get_or_create(
                            size=size,
                            defaults={
                                "price": price,
                                "sale_price": sale_price,
                                "quantity": self.quantity,
                            },
                        )
                        if not created:
                            variant.price = price
                            variant.sale_price = sale_price
                            variant.quantity = self.quantity
                            variant.save()
                except IntegrityError:
                    pass
                    

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = CloudinaryField('image', folder='products')

    def __str__(self):
        return f"{self.product.name} Image"


class ProductVariant(models.Model):
    SIZE_CHOICES = [
        ("S", "Small"),
        ("M", "Medium"),
        ("L", "Large"),
    ]
    product = models.ForeignKey(Product,on_delete=models.CASCADE, related_name = "variants")
    size = models.CharField(max_length=2,choices = SIZE_CHOICES)
    price = models.DecimalField(
        decimal_places=2,
        max_digits=8,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    sale_price = models.DecimalField( 
        decimal_places=2,
        max_digits=8,
        default=0,
    )
    quantity = models.PositiveIntegerField(default=0)
    image = CloudinaryField('image',folder="variants", blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product","size"],name = "unique_product_size")
        ]

    def __str__(self):
        return f"{self.product.name} - {self.get_size_display()}"
    

    @property
    def discount_percent(self):
        if self.price > 0 and self.sale_price > 0 and self.sale_price < self.price:
            return round(((self.price - self.sale_price) / self.price) * 100, 2)
        return 0
class VariantImage(models.Model):
        variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="variant_images")
        image = CloudinaryField('image',folder = 'variants')
        display_order = models.IntegerField(default=0)
        created_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            ordering = ['display_order']

        def __str__(self):
            return f"{self.variant.product.name} - {self.variant.get_size_display()} - Image {self.display_order}"



# ADDRESS

class Address(models.Model):
    address_id = models.AutoField(primary_key=True) 
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="store_addresses")
    full_name = models.CharField(max_length=100, default="Unknown")
    phone = models.CharField(max_length=15, default="0000000000")
    address_line = models.CharField(max_length=255, default="To be updated")
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=10, default="000000")  
    is_default = models.BooleanField(default=False)             

    def __str__(self):
        return f"{self.full_name}, {self.city}"












