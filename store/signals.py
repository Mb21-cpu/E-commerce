from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import Product


@receiver(post_save, sender=Product)
def check_low_stock(sender, instance, **kwargs):
    """
    Verificar stock bajo cuando se guarda un producto
    """
    # Umbral de stock bajo
    threshold = getattr(instance, 'stock_threshold', 5)

    # Verificar si el stock está por debajo del umbral y no es cero
    if instance.stock_quantity <= threshold and instance.stock_quantity > 0:
        print(f"⚠️ Alerta: {instance.name} tiene stock bajo ({instance.stock_quantity} unidades)")

        # Enviar email de alerta
        send_low_stock_alert(instance)


def send_low_stock_alert(product):
    """
    Enviar email de alerta de stock bajo
    """
    try:
        subject = f"⚠️ Alerta de Stock Bajo: {product.name}"

        # Mensaje simple en texto
        message = f"""
        ALERTA DE STOCK BAJO

        Producto: {product.name}
        SKU: {product.sku}
        Stock Actual: {product.stock_quantity} unidades
        Umbral Mínimo: {getattr(product, 'stock_threshold', 5)} unidades

        El stock de este producto ha caído por debajo del nivel mínimo.

        Acción recomendada:
        - Revisar inventario
        - Realizar pedido de reposición
        - Actualizar stock cuando llegue mercancía

        Para gestionar: http://127.0.0.1:8000/admin/store/product/{product.id}/change/
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        print(f"✅ Email de alerta enviado para: {product.name}")

    except Exception as e:
        print(f"❌ Error enviando alerta: {e}")