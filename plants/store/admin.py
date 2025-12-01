from django.contrib import admin
from .models import Category, Product, Address, ProductVariant, ProductImage
from cart.models import Cart
# from accounts.models import UserProfile

# Inline for ProductVariant
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('size', 'price', 'quantity', 'image')
    readonly_fields = ('get_size_display',)

    def get_size_display(self, obj):
        return obj.get_size_display()
    get_size_display.short_description = 'Size'

# Inline for ProductImage
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image',)

# Admin for Product
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_sale', 'quantity', 'status')
    list_filter = ('category', 'is_sale', 'status')
    search_fields = ('name', 'description')
    inlines = [ProductVariantInline, ProductImageInline]

# Admin for ProductVariant
@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'get_size_display', 'price', 'quantity')
    list_filter = ('product', 'size')
    search_fields = ('product__name',)
    fieldsets = (
        (None, {
            'fields': ('product', 'size', 'price', 'quantity', 'image')
        }),
    )

    def get_size_display(self, obj):
        return obj.get_size_display()
    get_size_display.short_description = 'Size'

# Admin for ProductImage
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image')
    list_filter = ('product',)
    search_fields = ('product__name',)

# Register other models
admin.site.register(Address)
admin.site.register(Cart)
admin.site.register(Category)
# admin.site.register(UserProfile)
