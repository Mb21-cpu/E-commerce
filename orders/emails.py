from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


def send_order_confirmation_email(order):
    """Enviar email de confirmación de pedido"""

    print(f"🔍 DEBUG: Iniciando envío de email para orden #{order.id}")
    print(f"🔍 DEBUG: Email destino: {order.customer_email}")

    subject = f'✅ Confirmación de Pedido #{order.id} - Mi Tienda'

    context = {
        'order': order,
        'customer_name': f"{order.customer_first_name} {order.customer_last_name}",
        'store_name': 'Mi Tienda',
        'support_email': 'soporte@mitienda.com'
    }

    try:
        print("🔍 DEBUG: Intentando renderizar template...")

        # VERIFICAR SI EL TEMPLATE EXISTE
        try:
            html_content = render_to_string('orders/emails/order_confirmation.html', context)
            print("✅ DEBUG: Template renderizado exitosamente")
        except Exception as template_error:
            print(f"❌ ERROR en template: {template_error}")
            # Fallback: crear contenido simple
            html_content = f"""
            <h1>Confirmación de Pedido #{order.id}</h1>
            <p>Hola {context['customer_name']},</p>
            <p>Tu pedido ha sido confirmado. Total: ${order.total_paid}</p>
            """

        text_content = strip_tags(html_content)

        print("🔍 DEBUG: Creando objeto Email...")
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.customer_email],
            reply_to=[settings.DEFAULT_FROM_EMAIL]
        )

        email.attach_alternative(html_content, "text/html")

        print("🔍 DEBUG: Enviando email...")
        email.send(fail_silently=False)
        print("✅ DEBUG: Email enviado exitosamente")
        return True

    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        import traceback
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
        return False

def send_order_shipped_email(order, tracking_number=None):
    """Enviar email cuando el pedido es enviado"""
    subject = f'🚚 Tu pedido #{order.id} ha sido enviado'

    context = {
        'order': order,
        'customer_name': f"{order.customer_first_name} {order.customer_last_name}",
        'tracking_number': tracking_number,
        'store_name': 'Mi Tienda'
    }

    html_content = render_to_string('orders/emails/order_shipped.html', context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.customer_email]
    )

    email.attach_alternative(html_content, "text/html")

    try:
        email.send()
        return True
    except Exception as e:
        print(f"Error enviando email de envío: {e}")
        return False