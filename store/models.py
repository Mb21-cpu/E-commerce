from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sku = models.CharField(max_length=100, unique=True)
    stock_quantity = models.IntegerField()
    available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products')
    meta_title = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Meta Título",
        help_text="Título para SEO (máx. 200 caracteres)"
    )
    meta_description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Meta Descripción",
        help_text="Descripción para SEO (máx. 300 caracteres)"
    )
    # 🆕 OPCIONAL: Umbral de stock configurable
    stock_threshold = models.IntegerField(
        default=5,
        verbose_name="Umbral de Stock Bajo",
        help_text="Nivel de stock para alertas (default: 5)"
    )



    def save(self, *args, **kwargs):
        """Generar slug automáticamente si no existe"""
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """URL para detalle del producto usando slug"""
        return reverse('product_detail', kwargs={'slug': self.slug})

    def reduce_stock(self, quantity):
        """Reducir stock de forma segura con verificación"""
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.save()
            print(f"✅ Stock reducido: {self.name} -{quantity} unidades")
            return True
        else:
            print(f"❌ Stock insuficiente: {self.name} (Stock: {self.stock_quantity}, Pedido: {quantity})")
            return False

    def get_availability(self):
        """Obtener disponibilidad del producto"""
        if self.stock_quantity <= 0:
            return "agotado"
        elif self.stock_quantity < 5:
            return "poco_stock"
        else:
            return "disponible"

    def get_availability_display(self):
        """Texto amigable para mostrar disponibilidad"""
        availability = self.get_availability()
        if availability == "agotado":
            return "🟥 Agotado"
        elif availability == "poco_stock":
            return f"🟨 Solo {self.stock_quantity} disponibles"
        else:
            return "🟩 En stock"

    def can_add_to_cart(self, quantity=1):
        """Verificar si se puede añadir al carrito"""
        return self.stock_quantity >= quantity

    def __str__(self):
        return f"{self.name} (Stock: {self.stock_quantity})"

    class Meta:
        ordering = ['-created_at']


class ProductImage(models.Model):
    """Modelo para múltiples imágenes por producto"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='products/images/',
        verbose_name="Imagen adicional"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Imagen de producto"
        verbose_name_plural = "Imágenes de producto"
        ordering = ['created_at']

    def __str__(self):
        return f"Imagen de {self.product.name}"

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f'Reseña de {self.user.username} para {self.product.name}'