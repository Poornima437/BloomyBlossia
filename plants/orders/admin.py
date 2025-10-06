from django.contrib import admin
from .models import Order, OrderItem, Review

class OrderItemInline(admin.TabularInline):  # show order items inside orders
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "user", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_id", "user__username")
    inlines = [OrderItemInline]

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("user__username", "product__name")
