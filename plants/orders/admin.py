# orders/admin.py

from django.contrib import admin
from .models import Order, OrderItem, Review


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'variant', 'quantity', 'price')  # ← Now safe to include
    readonly_fields = ('price', 'product', 'variant')  # Prevent accidental changes
    can_delete = False  # Better to cancel items via status than delete

    # Optional: make status more user-friendly
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'variant')

    # Optional: color-code status
    def status_display(self, obj):
        status = obj.status
        color = {
            'PLACED': 'blue',
            'CANCELED': 'red',
            'RETURNED': 'orange',
        }.get(status, 'black')
        return f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>'
    
    status_display.short_description = 'Item Status'
    status_display.allow_tags = True
    list_display = ('status_display',)  # Not needed in inline, but safe


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'status', 'total', 'payment_method', 'created_at', 'colored_status')
    list_filter = ('status', 'payment_method', 'created_at', 'return_request')
    search_fields = ('order_id', 'user__username', 'user__email')
    readonly_fields = ('order_id', 'created_at', 'updated_at', 'total', 'subtotal')
    inlines = [OrderItemInline]

    fieldsets = (
        ('Order Info', {
            'fields': ('order_id', 'user', 'status', 'payment_method', 'total', 'created_at')
        }),
        ('Shipping & Address', {
            'fields': ('address', 'order_notes'),
        }),
        ('Return/Cancel', {
            'fields': ('return_request', 'return_reason', 'cancel_reason', 'canceled_at'),
            'classes': ('collapse',),
        }),
    )

    def colored_status(self, obj):
        color = {
            'PLACED': '#1e90ff',
            'PACKED': '#32cd32',
            'SHIPPED': '#ffa500',
            'DELIVERED': '#28a745',
            'CANCELED': '#dc3545',
            'RETURNED': '#fd7e14',
        }.get(obj.status, '#6c757d')
        return f'<span style="color: white; background: {color}; padding: 3px 8px; border-radius: 4px; font-weight: bold;">{obj.get_status_display()}</span>'
    
    colored_status.short_description = 'Status'
    colored_status.allow_tags = True



@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at', 'comment_preview')
    list_filter = ('rating', 'created_at', 'product')
    search_fields = ('user__username', 'product__name', 'feedback')  # ← FIXED

    def comment_preview(self, obj):
        return (obj.feedback[:50] + '...') if obj.feedback and len(obj.feedback) > 50 else obj.feedback
    comment_preview.short_description = 'Feedback'

