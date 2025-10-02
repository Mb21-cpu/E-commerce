import stripe
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import views as auth_views
from django.views.generic import CreateView
from django.urls import reverse_lazy, reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import decimal
from decimal import Decimal

# Importa la función send_mail
from django.core.mail import send_mail
import traceback  # Para depuración

from .models import Product, ContactMessage
from orders.models import Order, OrderItem
from django.contrib.auth import get_user_model

# Inicializa Stripe con tu clave secreta
stripe.api_key = settings.STRIPE_SECRET_KEY


# --------------------
# Vistas Generales
# --------------------

def get_cart_count(request):
    """
    Función de ayuda para obtener el número total de productos en el carrito.
    """
    cart = request.session.get('cart', {})
    return sum(item['quantity'] for item in cart.values())


def product_list_view(request):
    """
    Muestra el catálogo de todos los productos.
    """
    products = Product.objects.all()
    cart_count = get_cart_count(request)
    context = {
        'products': products,
        'cart_count': cart_count,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY
    }
    return render(request, 'store/product_list.html', context)


def product_detail(request, slug):
    """
    Muestra los detalles de un solo producto, buscándolo por SLUG.
    """
    # Buscar por slug en lugar de ID
    product = get_object_or_404(Product, slug=slug, available=True)
    cart_count = get_cart_count(request)
    context = {
        'product': product,
        'cart_count': cart_count,
    }
    return render(request, 'store/product_detail.html', context)


def get_cart_count_view(request):
    """
    Devuelve solo el número total de productos en el carrito (para HTMX).
    """
    cart = request.session.get('cart', {})
    item_count = sum(item['quantity'] for item in cart.values())
    return HttpResponse(str(item_count))


# --------------------
# Vistas del Carrito
# --------------------

def add_to_cart(request, product_id):
    """
    Añade un producto al carrito de la sesión.
    """
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get('cart', {})
    product_id_str = str(product.id)

    if product.stock <= 0:
        message_html = f'<div class="floating-message error">¡Lo sentimos! Este producto está agotado.</div>'
        response = HttpResponse(message_html)
        response['HX-Trigger'] = 'updateCart'
        return response

    if product_id_str not in cart:
        cart[product_id_str] = {'quantity': 1, 'price': str(product.price), 'name': product.name}
    else:
        if cart[product_id_str]['quantity'] >= product.stock:
            message_html = f'<div class="floating-message error">¡No hay más stock para {product.name}!</div>'
            response = HttpResponse(message_html)
            response['HX-Trigger'] = 'updateCart'
            return response

        cart[product_id_str]['quantity'] += 1

    request.session['cart'] = cart
    item_count = sum(item['quantity'] for item in cart.values())

    message_html = f'<div class="floating-message">¡Añadiste {product.name}! Llevas {item_count} productos.</div>'
    response = HttpResponse(message_html)
    response['HX-Trigger'] = 'updateCart'

    return response


def cart_detail(request):
    """
    Muestra los productos del carrito y el total.
    """
    cart = request.session.get('cart', {})
    cart_items = []
    cart_total = 0
    if not request.user.is_authenticated:
        messages.info(request, "¡Regístrate o inicia sesión para guardar tu carrito y finalizar tu compra!")
    for key, item in cart.items():
        item['product_id'] = key
        item_total = float(item['price']) * item['quantity']
        cart_total += item_total
        item['total'] = item_total
        cart_items.append(item)
    cart_count = get_cart_count(request)
    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'cart_count': cart_count,
    }
    return render(request, 'store/cart_detail.html', context)


def update_cart(request, product_id):
    """
    Actualiza la cantidad de un producto en el carrito.
    """
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)

    if product_id_str in cart:
        action = request.POST.get('action')
        if action == 'increase':
            cart[product_id_str]['quantity'] += 1
        elif action == 'decrease' and cart[product_id_str]['quantity'] > 1:
            cart[product_id_str]['quantity'] -= 1

        request.session['cart'] = cart

    return redirect('cart_detail')


def remove_from_cart(request, product_id):
    """
    Elimina un producto del carrito.
    """
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)

    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        messages.success(request, "Producto eliminado del carrito.")

    return redirect('cart_detail')


# --------------------
# Vistas de Compra y Historial (MODIFICADA PARA USAR STRIPE)
# --------------------

@login_required
def checkout(request):
    """
    Crea una sesión de Checkout de Stripe y redirige al usuario a la pasarela de pago.
    """
    cart = request.session.get('cart', {})

    if not cart:
        messages.error(request, "Tu carrito está vacío.")
        return redirect('product_list')

    subtotal = sum(decimal.Decimal(item['price']) * item['quantity'] for item in cart.values())
    shipping_fee = decimal.Decimal(str(settings.SHIPPING_FEE))
    total_con_envio = subtotal + shipping_fee

    if request.method == 'POST':
        address = request.POST.get('address')

        if not address:
            messages.error(request, "Por favor, ingresa una dirección de envío.")
            return redirect('checkout')

        # 1. Preparar items para Stripe
        line_items = []
        for product_id, item_data in cart.items():
            product = get_object_or_404(Product, id=product_id)

            # Validación de stock, aunque se vuelve a validar en el webhook, es bueno chequear aquí
            if product.stock < item_data['quantity']:
                messages.error(request, f"Stock insuficiente para {product.name}.")
                return redirect('cart_detail')

            line_items.append({
                'price_data': {
                    'currency': settings.DEFAULT_CURRENCY,
                    'unit_amount': int(decimal.Decimal(item_data['price']) * 100),  # Stripe usa centavos
                    'product_data': {
                        'name': item_data['name'],
                        'description': product.description[:50],  # Breve descripción
                        # Aquí puedes añadir la URL de una imagen si tienes una ruta absoluta o pública
                    },
                },
                'quantity': item_data['quantity'],
            })

        # 2. Agregar el costo de envío como un line_item
        if shipping_fee > 0:
            line_items.append({
                'price_data': {
                    'currency': settings.DEFAULT_CURRENCY,
                    'unit_amount': int(shipping_fee * 100),
                    'product_data': {
                        'name': 'Costo de Envío',
                        'description': 'Tarifa de envío estándar',
                    },
                },
                'quantity': 1,
            })

        try:
            # 3. Crear la Sesión de Checkout en Stripe
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                # URLs de redirección
                success_url=request.build_absolute_uri(
                    reverse_lazy('payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri(reverse_lazy('checkout')),

                # Metadata para identificar la orden después del pago (¡IMPORTANTE!)
                metadata={
                    'customer_id': request.user.id,
                    'shipping_address': address,
                    # Aquí podemos guardar todo el carrito como JSON si fuera necesario
                },
                customer_email=request.user.email,
            )

            # Redirigir al usuario a la URL de pago de Stripe
            return redirect(checkout_session.url, code=303)

        except Exception as e:
            messages.error(request, f"Ocurrió un error al iniciar el pago: {str(e)}")
            return redirect('checkout')

    # Lógica para GET
    cart_count = get_cart_count(request)
    context = {
        'cart_items': cart.values(),
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'cart_total': total_con_envio,
        'cart_count': cart_count,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, 'store/checkout.html', context)


# --- FUNCIÓN DE ENVÍO DE CORREO ---
def send_order_confirmation_email(order):
    """
    Función de ayuda para enviar un correo de confirmación al cliente.
    """
    subject = f'Confirmación de tu compra #{order.id}'
    message = (
        f'Hola {order.customer.username},\n\n'
        f'¡Gracias por tu compra! Tu orden #{order.id} ha sido confirmada y tu pago ha sido procesado exitosamente.\n'
        f'Tu pedido será enviado a la siguiente dirección:\n'
        f'{order.shipping_address}\n\n'
        f'Total Pagado: ${order.total_paid:.2f}\n\n'
        f'Puedes ver los detalles completos de tu orden en tu historial de compras.\n\n'
        f'¡Gracias por preferirnos!\n'
        f'El equipo de tu tienda'
    )
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [order.customer_email]

    try:
        # Usa el fail_silently=True si quieres que los errores de correo no detengan la aplicación
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
    except Exception as e:
        print(f"Error al enviar el correo de confirmación: {e}")
        # Aquí podrías querer registrar el error o intentar un reenvío.


# Vistas de Redirección de Stripe (NUEVAS)
# -----------------------------------------------------

@login_required
def payment_success(request):
    """
    Esta vista crea la orden localmente si el pago de Stripe es exitoso
    y envía un correo de confirmación.
    """
    session_id = request.GET.get('session_id')
    if not session_id:
        messages.error(request, "No se encontró ID de sesión de Stripe.")
        return redirect('purchase_history')

    if Order.objects.filter(stripe_checkout_session_id=session_id).exists():
        messages.info(request, "Esta orden ya ha sido registrada.")
        return redirect('purchase_history')

    try:
        # Intenta recuperar la sesión de Stripe (puede fallar si el ID es inválido o no existe)
        session = stripe.checkout.Session.retrieve(session_id)

        # Si el pago fue exitoso, creamos la orden localmente.
        if session.payment_status == 'paid':
            user_id = session.metadata.get('customer_id')
            shipping_address = session.metadata.get('shipping_address')
            # Usar 'amount_total' de la sesión de Stripe
            total_paid = decimal.Decimal(session.amount_total / 100)

            User = get_user_model()
            customer = User.objects.get(id=user_id)

            # 1. Crear la Orden principal
            order = Order.objects.create(
                customer=customer,
                customer_email=session.customer_details['email'],
                shipping_address=shipping_address,
                total_paid=total_paid,
                stripe_checkout_session_id=session_id
            )

            # 2. Obtener los productos de la sesión de Stripe y crear los OrderItems
            # NOTA: session.line_items no siempre está cargado, es mejor usar Session.list_line_items
            line_items = stripe.checkout.Session.list_line_items(session_id, limit=100)

            for item in line_items.data:
                # Excluimos el costo de envío
                if 'Costo de Envío' in item.description:
                    continue

                try:
                    # Buscamos el producto por el nombre guardado en Stripe
                    product_name = item.description
                    product = Product.objects.get(name=product_name)

                    item_quantity = item.quantity
                    # item.amount_total es el total del line_item (precio * cantidad)
                    item_price_total = decimal.Decimal(item.amount_total / 100)
                    item_price = item_price_total / item_quantity  # Precio unitario

                    # 3. Descontar stock
                    product.stock -= item_quantity
                    product.save()

                    # 4. Crear el Item de la Orden
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        price=item_price,
                        quantity=item_quantity
                    )
                except Product.DoesNotExist:
                    print(f"Advertencia: Producto '{product_name}' no encontrado. OrdenItem no creado.")
                    continue

            # 5. Vaciar el carrito de la sesión
            if 'cart' in request.session:
                del request.session['cart']
                request.session.modified = True

            # 6. Envío de Correo
            send_order_confirmation_email(order)

            messages.success(request,
                             f"¡Pago exitoso! Tu orden #{order.id} ha sido registrada y se ha enviado un correo de confirmación.")
            return redirect('purchase_history')
        else:
            messages.error(request, "El pago no se completó. Por favor, inténtalo de nuevo.")
            return redirect('checkout')

    # Manejo de cualquier error de la API de Stripe o de red.
    except Exception as e:
        messages.error(request, f"Ocurrió un error inesperado durante la verificación del pago: {str(e)}")
        # Para depuración, imprime el error completo
        traceback.print_exc()
        return redirect('checkout')


@login_required
def payment_cancel(request):
    """
    Vista a la que Stripe redirige si el usuario cancela el pago.
    """
    messages.warning(request, "El proceso de pago ha sido cancelado. Puedes intentarlo de nuevo.")
    return redirect('checkout')


@csrf_exempt
def stripe_webhook(request):
    """
    Esta vista NO SE UTILIZARÁ en tu entorno local debido a la falta de Stripe CLI.
    La mantenemos para futuras implementaciones en producción.
    """
    return HttpResponse(status=200)


@login_required
def order_detail(request, order_id):
    """
    Muestra los detalles de una orden específica (solo si pertenece al usuario).
    """
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    # Los items de la orden se obtienen automáticamente gracias a related_name en OrderItem
    items = OrderItem.objects.filter(order=order)
    cart_count = get_cart_count(request)

    context = {
        'order': order,
        'items': items,
        'cart_count': cart_count,
    }
    return render(request, 'store/order_detail.html', context)


@login_required
def purchase_history_view(request):
    """
    Muestra el historial de compras del usuario autenticado.
    """
    # Se corrige el nombre del campo a '-created' para ordenar por fecha de creación
    orders = Order.objects.filter(customer=request.user).order_by('-created')
    cart_count = get_cart_count(request)
    context = {
        'orders': orders,
        'cart_count': cart_count,
    }
    return render(request, 'store/purchase_history.html', context)


@staff_member_required
def delete_purchase_history(request):
    """
    Elimina el historial de compras de un usuario (solo para administradores).
    """
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            Order.objects.filter(customer_id=user_id).delete()
            messages.success(request, "El historial de compras del usuario ha sido eliminado.")
            return redirect('purchase_history')
        else:
            messages.error(request, "Falta el ID de usuario para eliminar el historial.")
            return redirect('purchase_history')

    messages.error(request, "Acción no permitida.")
    return redirect('purchase_history')


# --------------------
# Vistas de Autenticación
# --------------------

class SignUpView(CreateView):
    """
    Maneja el registro de nuevos usuarios.
    """
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'


def password_reset_request(request):
    """
    Vista para solicitar el email de reseteo de contraseña.
    """
    return auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        success_url=reverse_lazy('password_reset_done')
    )(request)


def password_reset_done(request):
    """
    Vista de confirmación de email enviado.
    """
    return auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    )(request)


def password_reset_confirm(request, uidb64, token):
    """
    Vista para establecer la nueva contraseña.
    """
    return auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete')
    )(request, uidb64=uidb64, token=token)


def password_reset_complete(request):
    """
    Vista de confirmación de contraseña cambiada.
    """
    return auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    )(request)


def contact_view(request):
    """
    Procesa el formulario de contacto y renderiza la página.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Crea y guarda el nuevo mensaje en la base de datos
        ContactMessage.objects.create(name=name, email=email, message=message)

        # Muestra un mensaje de éxito
        messages.success(request,
                         '¡Gracias! Tu mensaje ha sido enviado correctamente y nos pondremos en contacto contigo pronto.')

        # Redirige al usuario a la misma página para evitar envíos duplicados
        return redirect('contact')

    cart_count = get_cart_count(request)
    context = {
        'cart_count': cart_count,
    }
    return render(request, 'store/contact.html', context)
