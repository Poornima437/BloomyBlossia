from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from cloudinary.models import CloudinaryField
from django.utils import timezone



# USER PROFILE
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_image = CloudinaryField('image', folder='profile', blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    phone = models.CharField(max_length=15, blank=True)
    

    def __str__(self):
        return self.user.username

    @property
    def get_profile_image(self):
        try:
            if self.profile_image and getattr(self.profile_image, 'url', None):
                return self.profile_image.url
        except Exception:
            pass
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



