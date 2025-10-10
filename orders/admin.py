from django.contrib import admin
from .models import Order, OrderItem, Coupon

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_email', 'total_paid', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['customer_email', 'customer_first_name', 'customer_last_name']
    inlines = [OrderItemInline]
    readonly_fields = ['created_at', 'updated_at']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']
    list_filter = ['order__status']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_value', 'discount_type', 'is_active', 'created_at']
    list_filter = ['is_active', 'discount_type', 'created_at']
    search_fields = ['code']
    list_editable = ['is_active']

    fieldsets = (
        ('Información del Cupón', {
            'fields': ('code', 'is_active')
        }),
        ('Configuración del Descuento', {
            'fields': ('discount_type', 'discount_value')
        }),
    )