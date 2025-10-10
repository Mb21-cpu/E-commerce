from django.db import models
from django.contrib.auth.models import User
from store.models import Product


class Order(models.Model):
    PENDING = 'pending'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (PENDING, 'Pendiente'),
        (COMPLETED, 'Completado'),
        (CANCELLED, 'Cancelado'),
    ]

    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customer_email = models.EmailField()
    customer_first_name = models.CharField(max_length=100, default='')
    customer_last_name = models.CharField(max_length=100, default='')
    shipping_address = models.TextField(default='')
    city = models.CharField(max_length=100, default='')
    postal_code = models.CharField(max_length=20, default='')
    country = models.CharField(max_length=100, default='España')
    total_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    stripe_payment_intent = models.CharField(max_length=200, blank=True)

    # 🆕 CAMPOS NUEVOS PARA CUPONES
    applied_coupon = models.ForeignKey(
        'Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Cupón aplicado"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Monto de descuento"
    )

    def __str__(self):
        return f"Order {self.id} - {self.customer_email}"

    class Meta:
        db_table = 'orders_order'
        ordering = ['-created_at']

    # 🆕 MÉTODO NUEVO PARA CALCULAR SUBTOTAL
    def get_subtotal(self):
        """Calcula el subtotal sin descuentos"""
        return sum(item.get_total_price() for item in self.items.all())

    def get_total_items(self):
        """Obtener el total de items en el pedido"""
        return sum(item.quantity for item in self.items.all())

    def get_status_display_class(self):
        """Obtener clase CSS para el estado"""
        status_classes = {
            'pending': 'status-pending',
            'completed': 'status-completed',
            'cancelled': 'status-cancelled',
        }
        return status_classes.get(self.status, 'status-pending')

    def get_status_badge(self):
        """Obtener badge con icono para el estado"""
        status_badges = {
            'pending': '🕒 Pendiente',
            'completed': '✅ Completado',
            'cancelled': '❌ Cancelado',
        }
        return status_badges.get(self.status, '🕒 Pendiente')


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    class Meta:
        db_table = 'orders_orderitem'

    def get_total_price(self):
        return self.quantity * self.price


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('PERCENTAGE', 'Porcentaje'),
        ('FIXED_AMOUNT', 'Cantidad Fija'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name="Código")
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor del descuento"
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        verbose_name="Tipo de descuento"
    )
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        verbose_name = "Cupón"
        verbose_name_plural = "Cupones"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()}: {self.discount_value})"

    def calculate_discount(self, total_amount):
        """Calcula el monto del descuento basado en el total"""
        if self.discount_type == 'PERCENTAGE':
            discount = total_amount * (self.discount_value / 100)
        else:  # FIXED_AMOUNT
            discount = min(self.discount_value, total_amount)  # No más que el total

        return round(discount, 2)