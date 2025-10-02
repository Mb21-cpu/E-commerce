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

# IMPORTANTE: Asegúrate de que Category y Product estén importados
from .models import Product, ContactMessage, Category
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


def product_list(request, category_slug=None):
    """
    Muestra el catálogo de productos, opcionalmente filtrado por categoría (category_slug).
    """
    # 1. Obtener todas las categorías para el menú de navegación (base.html)
    categories = Category.objects.all()

    # 2. Preparar los productos
    products = Product.objects.filter(available=True)
    current_category = None

    # 3. Filtrar por categoría si se proporciona un slug
    if category_slug:
        # Aseguramos que la categoría exista, si no, devuelve un 404
        current_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=current_category)

    cart_count = get_cart_count(request)

    context = {
        'categories': categories,  # Lista de todas las categorías
        'products': products,  # Lista de productos (filtrados o todos)
        'current_category': current_category,  # Categoría seleccionada (para el título y el menú activo)
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
    categories = Category.objects.all()

    context = {
        'product': product,
        'cart_count': cart_count,
        'categories': categories,
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
        current_quantity = cart[product_id_str]['quantity']
        if current_quantity >= product.stock:
            message_html = f'<div class="floating-message error">¡No hay más stock para {product.name}!</div>'
            response = HttpResponse(message_html)
            response['HX-Trigger'] = 'updateCart'
            return response

        cart[product_id_str]['quantity'] += 1

    request.session['cart'] = cart
    item_count = sum(item['quantity'] for item in cart.values())

    # Usamos hx-swap="none" en el botón, por lo que este HTML solo se usa para el mensaje flotante
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
        try:
            # Intentamos obtener el producto para tener la imagen o más detalles
            product = Product.objects.get(id=key)
            item['image_url'] = product.image.url if product.image else None
        except Product.DoesNotExist:
            item['image_url'] = None

        item['product_id'] = key
        item_total = float(item['price']) * item['quantity']
        cart_total += item_total
        item['total'] = item_total
        cart_items.append(item)

    cart_count = get_cart_count(request)
    categories = Category.objects.all()

    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'cart_count': cart_count,
        'categories': categories,
    }
    return render(request, 'store/cart_detail.html', context)


def update_cart(request, product_id):
    """
    Actualiza la cantidad de un producto en el carrito.
    """
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    product = get_object_or_404(Product, id=product_id)

    if product_id_str in cart:
        action = request.POST.get('action')
        current_quantity = cart[product_id_str]['quantity']

        if action == 'increase':
            if current_quantity < product.stock:
                cart[product_id_str]['quantity'] += 1
            else:
                messages.error(request, f"Límite de stock ({product.stock}) alcanzado para {product.name}.")
        elif action == 'decrease' and current_quantity > 1:
            cart[product_id_str]['quantity'] -= 1

        request.session['cart'] = cart
        request.session.modified = True

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
        request.session.modified = True
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

    # Convertir a Decimal para cálculos precisos
    subtotal = sum(Decimal(item['price']) * item['quantity'] for item in cart.values())
    shipping_fee = Decimal(str(settings.SHIPPING_FEE))
    total_con_envio = subtotal + shipping_fee

    if request.method == 'POST':
        address = request.POST.get('address')

        if not address:
            messages.error(request, "Por favor, ingresa una dirección de envío.")
            return redirect('checkout')

        # 1. Preparar items para Stripe
        line_items = []
        for product_id_str, item_data in cart.items():
            product = get_object_or_404(Product, id=int(product_id_str))

            # Validación de stock
            if product.stock < item_data['quantity']:
                messages.error(request, f"Stock insuficiente para {product.name}.")
                return redirect('cart_detail')

            line_items.append({
                'price_data': {
                    'currency': settings.DEFAULT_CURRENCY,
                    # Stripe usa centavos, por eso multiplicamos por 100 y convertimos a int
                    'unit_amount': int(Decimal(item_data['price']) * 100),
                    'product_data': {
                        'name': item_data['name'],
                        'description': product.description[:50] if product.description else 'Producto de la tienda',
                        # CRÍTICO: PASAR EL ID DEL PRODUCTO DE DJANGO EN LA METADATA
                        'metadata': {
                            'product_id': product_id_str,
                        }
                    },
                },
                'quantity': item_data['quantity'],
            })

        # 2. Agregar el costo de envío como un line_item (si es mayor a cero)
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
                    # Ya no necesitamos guardar todo el carrito aquí, usamos la metadata del line_item
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
    categories = Category.objects.all()

    context = {
        'cart_items': cart.values(),
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'cart_total': total_con_envio,
        'cart_count': cart_count,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'categories': categories,
    }
    return render(request, 'store/checkout.html', context)


# --- FUNCIÓN DE ENVÍO DE CORREO ---
def send_order_confirmation_email(order):
    """
    Función de ayuda para enviar un correo de confirmación al cliente.
    """
    subject = f'Confirmación de tu compra #{order.id}'
    # Usar el nombre de usuario del cliente si está disponible, si no, usar el correo
    customer_identifier = order.customer.username if order.customer else order.customer_email

    message = (
        f'Hola {customer_identifier},\n\n'
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
        # Asegúrate de que settings.EMAIL_HOST_USER esté configurado
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
    except Exception as e:
        print(f"Error al enviar el correo de confirmación: {e}")


# Vistas de Redirección de Stripe (NUEVAS)
# -----------------------------------------------------

@login_required
def payment_success(request):
    """
    Esta vista crea la orden localmente si el pago de Stripe es exitoso
    y envía un correo de confirmación.

    CORRECCIÓN CRÍTICA: Se modificó la lógica para usar el product_id
    guardado en la metadata del line item de Stripe, en lugar de confiar
    en el nombre del producto, lo que es mucho más robusto.
    """
    session_id = request.GET.get('session_id')
    if not session_id:
        messages.error(request, "No se encontró ID de sesión de Stripe.")
        return redirect('purchase_history')

    # Evita que una orden se cree dos veces si el usuario refresca la página
    # Se debe verificar si el objeto Order ya fue creado
    if Order.objects.filter(stripe_checkout_session_id=session_id).exists():
        order = Order.objects.get(stripe_checkout_session_id=session_id)
        messages.info(request, f"Esta orden (#{order.id}) ya ha sido registrada.")
        # Simplemente redirigimos al detalle de la orden existente
        return redirect('order_detail', order_id=order.id)


    try:
        # 1. Recuperar la sesión de Stripe
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == 'paid':
            user_id = session.metadata.get('customer_id')
            shipping_address = session.metadata.get('shipping_address')
            # Stripe amount_total está en centavos. Dividimos por 100 para obtener el valor correcto en Decimal
            total_paid = Decimal(session.amount_total / 100)

            User = get_user_model()
            customer = User.objects.get(id=user_id)

            # 2. Crear la Orden principal
            order = Order.objects.create(
                customer=customer,
                customer_email=session.customer_details['email'],
                shipping_address=shipping_address,
                total_paid=total_paid,
                stripe_checkout_session_id=session_id
            )

            # 3. Obtener los productos de la sesión de Stripe y crear los OrderItems
            # NOTA: Debemos expandir los line_items para obtener la metadata del producto
            # Se usa `expand=['data.price.product']` para que Stripe incluya los detalles del producto
            line_items = stripe.checkout.Session.list_line_items(
                session_id,
                expand=['data.price.product'], # Expandir para acceder a la metadata del producto
                limit=100
            )

            for item in line_items.data:
                # Omitir el item de envío buscando la metadata del producto, que solo lo tienen los productos reales
                product_metadata = item.price.product.metadata if item.price.product and item.price.product.metadata else {}
                product_id_str = product_metadata.get('product_id')

                if not product_id_str:
                    # Si no hay product_id, asumimos que es el costo de envío o un item no mapeado
                    continue

                try:
                    # CRÍTICO: OBTENER EL ID DE DJANGO DE LA METADATA DE STRIPE
                    product = Product.objects.get(id=int(product_id_str))

                    item_quantity = item.quantity
                    item_price_total = Decimal(item.amount_total / 100)
                    item_price = item_price_total / item_quantity  # Precio unitario

                    # 4. Descontar stock
                    product.stock -= item_quantity
                    product.save()

                    # 5. Crear el Item de la Orden
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        price=item_price,
                        quantity=item_quantity
                    )
                except Product.DoesNotExist:
                    # Esto debe ser muy raro si la metadata fue bien configurada
                    print(f"Advertencia: Producto con ID '{product_id_str}' no encontrado. OrdenItem no creado.")
                    continue
                except Exception as e:
                    print(f"Error al procesar OrderItem: {e}")
                    continue

            # 6. Vaciar el carrito de la sesión
            # Esto debe hacerse AHORA, después de que todos los items se hayan guardado correctamente
            if 'cart' in request.session:
                del request.session['cart']
                request.session.modified = True

            # 7. Envío de Correo
            send_order_confirmation_email(order)

            messages.success(request,
                             f"¡Pago exitoso! Tu orden #{order.id} ha sido registrada y se ha enviado un correo de confirmación.")
            return redirect('order_detail', order_id=order.id) # Redirigir al detalle de la orden
        else:
            # El pago no está en estado 'paid'
            messages.error(request, "El pago no se completó. Por favor, inténtalo de nuevo.")
            return redirect('checkout')

    except stripe.error.StripeError as e:
        messages.error(request, f"Error de Stripe durante la verificación: {str(e)}")
        traceback.print_exc()
        return redirect('checkout')
    except Exception as e:
        messages.error(request, f"Ocurrió un error inesperado durante la verificación del pago: {str(e)}")
        tracebox.print_exc()
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
    Esta vista maneja los eventos de Stripe de forma asíncrona.
    En un entorno de producción, se usaría para crear la orden
    en lugar de 'payment_success' para mayor robustez.
    """
    # Esta vista debe verificar la firma del webhook y procesar eventos.
    # Por ahora, solo es un esqueleto. En el flujo actual, la orden se crea en payment_success.
    return HttpResponse(status=200)


@login_required
def order_detail(request, order_id):
    """
    Muestra los detalles de una orden específica (solo si pertenece al usuario).
    """
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    # Ya no se necesita el filtro adicional, el template usa order.items.all
    cart_count = get_cart_count(request)
    categories = Category.objects.all()

    context = {
        'order': order,
        'cart_count': cart_count,
        'categories': categories,
    }
    return render(request, 'store/order_detail.html', context)


@login_required
def purchase_history_view(request):
    """
    Muestra el historial de compras del usuario autenticado.
    """
    orders = Order.objects.filter(customer=request.user).order_by('-created')
    cart_count = get_cart_count(request)
    categories = Category.objects.all()

    context = {
        'orders': orders,
        'cart_count': cart_count,
        'categories': categories,
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
            # CORRECCIÓN: Usar 'customer' o 'user' según tu modelo Order.
            # Según tu modelo, el campo es `customer` (o `user` en el modelo proporcionado).
            # Me guío por la vista `purchase_history_view` que usa `customer=request.user`.
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

        ContactMessage.objects.create(name=name, email=email, message=message)
        messages.success(request,
                         '¡Gracias! Tu mensaje ha sido enviado correctamente y nos pondremos en contacto contigo pronto.')
        return redirect('contact')

    cart_count = get_cart_count(request)
    categories = Category.objects.all()

    context = {
        'cart_count': cart_count,
        'categories': categories,
    }
    return render(request, 'store/contact.html', context)
