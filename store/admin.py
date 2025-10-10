from django.contrib import admin
from .models import Category, Product, ProductImage,Review

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'preview']
    readonly_fields = ['preview']

    def preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" style="max-height: 50px; max-width: 50px;" />'
        return "No image"
    preview.allow_tags = True

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock_quantity', 'available', 'created_at']
    list_filter = ['available', 'category', 'created_at']
    search_fields = ['name', 'description', 'sku']
    prepopulated_fields = {'slug': ('name',)}  # Genera slug automáticamente

    # 🆕 FIELDS EXPLÍCITOS - INCLUIR SLUG
    fields = [
        'name',
        'slug',  # ✅ DEBE ESTAR AQUÍ
        'description',
        'category',
        'price',
        'sku',
        'stock_quantity',
        'stock_threshold',
        'available',
        'image',
        'meta_title',
        'meta_description',
        'created_at',
        'updated_at'
    ]

    readonly_fields = ('created_at', 'updated_at')  # Slug NO es readonly

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']