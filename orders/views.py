import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from accounts.models import Address
from cart.cart import Cart
from .models import Order, OrderItem
from .forms import CheckoutForm
from django.db import models
from .emails import send_order_confirmation_email, send_order_shipped_email

# Configurar Stripe - VERIFICACIÓN EXPLÍCITA
print("=== INICIALIZANDO STRIPE ===")
print(f"STRIPE_PUBLISHABLE_KEY: {settings.STRIPE_PUBLISHABLE_KEY}")
print(f"STRIPE_SECRET_KEY: {settings.STRIPE_SECRET_KEY}")

if not settings.STRIPE_PUBLISHABLE_KEY or not settings.STRIPE_SECRET_KEY:
    print("❌ ERROR: Claves de Stripe no configuradas correctamente")
else:
    print("✅ Claves de Stripe configuradas correctamente")
    stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def checkout_view(request):
    cart = Cart(request)

    # ✅ ACTUALIZAR CARRITO BASADO EN STOCK ACTUAL
    cart_updated = cart.update_quantities_based_on_stock()
    if cart_updated:
        messages.warning(request, "⚠️ Se actualizó tu carrito por cambios en el stock")
        return redirect('cart_detail')

    # ✅ VALIDAR STOCK ANTES DE PROCESAR PAGO
    errors, warnings = cart.check_stock_availability()

    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('cart_detail')

    for warning in warnings:
        messages.warning(request, warning)

    if not cart:
        messages.error(request, "Tu carrito está vacío.")
        return redirect('cart_detail')

    # ✅ OBTENER DIRECCIONES DEL USUARIO
    user_addresses = Address.objects.filter(user=request.user)
    default_address = user_addresses.filter(is_default=True).first()

    # VERIFICAR SI STRIPE ESTÁ CONFIGURADO
    stripe_pub_key = getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '')
    stripe_secret_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

    stripe_configured = bool(stripe_pub_key and stripe_secret_key and
                             stripe_pub_key.startswith('pk_test_') and
                             stripe_secret_key.startswith('sk_test_'))

    print(f"DEBUG: Stripe configurado: {stripe_configured}")
    print(f"DEBUG: Pub Key: {stripe_pub_key}")

    # 🆕 OBTENER INFORMACIÓN DEL DESCUENTO
    discount_amount = cart.get_discount_amount()
    total_with_discount = cart.get_total_with_discount()
    applied_coupon = cart.get_coupon()

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                # Crear el pedido
                order = form.save(commit=False)
                order.customer = request.user
                order.customer_email = form.cleaned_data['email']
                order.customer_first_name = form.cleaned_data['first_name']
                order.customer_last_name = form.cleaned_data['last_name']

                # 🆕 USAR TOTAL CON DESCUENTO
                order.total_paid = total_with_discount
                order.status = Order.PENDING

                # 🆕 GUARDAR INFORMACIÓN DEL CUPÓN
                if applied_coupon:
                    order.applied_coupon = applied_coupon
                    order.discount_amount = discount_amount

                order.save()

                # Crear items del pedido
                for item in cart:
                    OrderItem.objects.create(
                        order=order,
                        product=item['product'],
                        quantity=item['quantity'],
                        price=item['price']
                    )

                # DECISIÓN: ¿Stripe real o simulación?
                if not stripe_configured:
                    messages.warning(request, "Stripe no configurado. Usando modo simulación.")
                    return redirect('payment_simulation', order_id=order.id)

                # STRIPE REAL - USANDO PAYMENT INTENT (TU TEMPLATE PERSONALIZADO)
                try:
                    # 🆕 CALCULAR MONTO CORRECTO PARA STRIPE (con descuento)
                    amount_to_charge = int(total_with_discount * 100)  # Stripe usa centavos

                    print(f"💰 Creando Payment Intent por: ${total_with_discount} ({amount_to_charge} centavos)")

                    # 🆕 CREAR PAYMENT INTENT CON DESCUENTO
                    intent = stripe.PaymentIntent.create(
                        amount=amount_to_charge,
                        currency='usd',
                        metadata={
                            'order_id': order.id,
                            'customer_email': order.customer_email,
                            'discount_amount': str(discount_amount),
                            'applied_coupon_id': str(applied_coupon.id) if applied_coupon else '',
                        },
                        # 🆕 AGREGAR DESCRIPCIÓN
                        description=f"Pedido #{order.id} - {order.customer_email}"
                    )

                    order.stripe_payment_intent = intent.id
                    order.save()

                    print(f"✅ Payment Intent creado: {intent.id}")
                    print(f"✅ Client Secret: {intent.client_secret[:20]}...")

                    # 🆕 CONTEXT CON INFORMACIÓN DEL DESCUENTO PARA TU TEMPLATE
                    context = {
                        'order': order,
                        'client_secret': intent.client_secret,
                        'stripe_publishable_key': stripe_pub_key,
                        'total': total_with_discount,
                        'discount_amount': discount_amount,
                        'applied_coupon': applied_coupon,
                    }

                    # 🆕 REDIRIGIR A TU TEMPLATE PERSONALIZADO
                    return render(request, 'orders/stripe_payment.html', context)

                except Exception as e:
                    print(f"❌ Error en Stripe Payment Intent: {e}")
                    import traceback
                    traceback.print_exc()
                    messages.error(request, f"Error procesando el pago: {str(e)}")
                    return redirect('payment_simulation', order_id=order.id)

            except Exception as e:
                messages.error(request, f'Error creando la orden: {str(e)}')
                import traceback
                traceback.print_exc()
                return render(request, 'orders/checkout.html', {
                    'form': form,
                    'cart': cart,
                    'total': total_with_discount,
                    'user_addresses': user_addresses,
                    'default_address': default_address,
                    'stripe_configured': stripe_configured,
                    'discount_amount': discount_amount,
                    'applied_coupon': applied_coupon,
                })

    else:
        # ✅ PRECARGAR FORMULARIO CON DIRECCIÓN POR DEFECTO
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name or '',
                'email': request.user.email,
            }

            # Si hay dirección por defecto, precargar los campos
            if default_address:
                initial_data.update({
                    'first_name': default_address.full_name.split(' ')[
                        0] if ' ' in default_address.full_name else default_address.full_name,
                    'last_name': ' '.join(
                        default_address.full_name.split(' ')[1:]) if ' ' in default_address.full_name else '',
                    'address': default_address.street_address,
                    'city': default_address.city,
                    'postal_code': default_address.postal_code,
                    'country': default_address.country,
                })

        form = CheckoutForm(initial=initial_data)

    return render(request, 'orders/checkout.html', {
        'form': form,
        'cart': cart,
        'total': total_with_discount,
        'stripe_configured': stripe_configured,
        'user_addresses': user_addresses,
        'default_address': default_address,
        'discount_amount': discount_amount,
        'applied_coupon': applied_coupon,
    })


def stripe_payment_success(request, order_id):
    """Vista para éxito de pago con Stripe"""
    order = get_object_or_404(Order, id=order_id)

    try:
        if order.stripe_payment_intent:
            # 🆕 VERIFICAR EL PAGO EN STRIPE
            payment_intent = stripe.PaymentIntent.retrieve(order.stripe_payment_intent)
            print(f"🔍 Verificando Payment Intent: {payment_intent.status}")

            if payment_intent.status == 'succeeded':
                messages.success(request, f'¡Pago exitoso! Pedido #{order.id}')
                order.status = Order.COMPLETED
                order.save()

                # 🆕 PROCESAR LA ORDEN COMPLETA
                return process_successful_order(request, order)
            else:
                messages.warning(request, f'El pago no se completó. Estado: {payment_intent.status}')
                return redirect('order_detail', order_id=order_id)

    except Exception as e:
        print(f"❌ Error verificando pago: {e}")
        messages.warning(request, f'No se pudo verificar el pago: {str(e)}')

    # Si llegamos aquí, hubo un problema con el pago
    return redirect('order_detail', order_id=order_id)


def payment_cancel(request):
    """Vista cuando el usuario cancela el pago en Stripe"""
    messages.info(request, "El pago fue cancelado. Puedes intentarlo nuevamente cuando estés listo.")
    return redirect('cart_detail')


def process_successful_order(request, order):
    """Función central para procesar órdenes exitosas"""
    print(f"🎯 Procesando orden exitosa #{order.id}")

    # 1. Completar la orden si no está completa
    if order.status == Order.PENDING:
        order.status = Order.COMPLETED
        order.save()
        print(f"✅ Orden #{order.id} marcada como COMPLETADA")

    # 2. Actualizar stock
    for item in order.items.all():
        if item.product.stock_quantity >= item.quantity:
            item.product.stock_quantity -= item.quantity
            item.product.save()
            print(f"✅ Stock actualizado: {item.product.name} -{item.quantity} unidades")
        else:
            print(f"⚠️ Stock insuficiente para {item.product.name}")

    # 3. ✅ LIMPIAR CARRITO DEFINITIVAMENTE
    print("💥 LIMPIANDO CARRITO...")
    clear_cart_after_payment(request, order)

    # 4. Enviar email de confirmación
    try:
        send_order_confirmation_email(order)
        messages.success(request, "📧 Email de confirmación enviado")
        print("✅ Email de confirmación enviado")
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        messages.warning(request, "⚠️ Pedido completado, pero hubo un error enviando el email.")

    # 5. Redirigir a página de éxito
    return render(request, 'orders/order_success.html', {'order': order})


def payment_simulation(request, order_id):
    """Vista para simulación de pago (cuando Stripe no está configurado)"""
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        # Simular pago exitoso
        order.status = Order.COMPLETED
        order.save()
        return process_successful_order(request, order)

    return render(request, 'orders/payment_simulation.html', {'order': order})


def order_success(request, order_id):
    """Vista para mostrar éxito de orden (backup)"""
    order = get_object_or_404(Order, id=order_id)

    if order.status == Order.PENDING:
        order.status = Order.COMPLETED
        order.save()
        return process_successful_order(request, order)

    return render(request, 'orders/order_success.html', {'order': order})


def clear_cart_after_payment(request, order):
    """Elimina específicamente los productos comprados del carrito"""
    print(f"🛒 Limpiando carrito después del pago de orden #{order.id}")

    # Obtener IDs de productos comprados en esta orden
    purchased_product_ids = [str(item.product.id) for item in order.items.all()]
    print(f"📦 Productos comprados: {purchased_product_ids}")

    # Obtener el carrito actual
    cart = request.session.get('cart', {})
    print(f"🔍 Carrito antes: {len(cart)} productos")

    # Eliminar SOLO los productos que fueron comprados
    products_removed = []
    for product_id in purchased_product_ids:
        if product_id in cart:
            del cart[product_id]
            products_removed.append(product_id)
            print(f"🗑️ Eliminado producto {product_id} del carrito")

    # Actualizar la sesión
    request.session['cart'] = cart
    request.session.modified = True

    print(f"✅ Carrito después: {len(cart)} productos")
    print(f"📝 Productos removidos: {products_removed}")

    return len(products_removed) > 0


@login_required
def order_history(request):
    """Mostrar historial de pedidos del usuario"""
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')

    # Estadísticas para el dashboard
    total_orders = orders.count()
    completed_orders = orders.filter(status=Order.COMPLETED).count()
    total_spent = orders.filter(status=Order.COMPLETED).aggregate(
        total=models.Sum('total_paid')
    )['total'] or 0

    return render(request, 'orders/order_history.html', {
        'orders': orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'total_spent': total_spent,
    })


@login_required
def order_detail(request, order_id):
    """Mostrar detalle de un pedido específico"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


# Vista opcional de prueba para emails
@login_required
def test_email(request, order_id):
    """Vista para probar emails (solo desarrollo)"""
    if not settings.DEBUG:
        return redirect('order_history')

    order = get_object_or_404(Order, id=order_id, customer=request.user)

    try:
        email_sent = send_order_confirmation_email(order)
        if email_sent:
            messages.success(request, "✅ Email de prueba enviado correctamente")
        else:
            messages.error(request, "❌ Error enviando email de prueba")
    except Exception as e:
        messages.error(request, f"❌ Error: {str(e)}")

    return redirect('order_detail', order_id=order_id)


# Función de debugging
def debug_cart_status(request, message=""):
    """Función para debuguear el estado del carrito"""
    print(f"\n🔍 DEBUG CARRITO {message}:")
    print(f"Session keys: {list(request.session.keys())}")

    # Verificar todas las posibles claves de carrito
    possible_cart_keys = ['cart', 'shopping_cart', 'cart_items']
    if hasattr(settings, 'CART_SESSION_ID'):
        possible_cart_keys.append(settings.CART_SESSION_ID)

    for key in possible_cart_keys:
        if key in request.session:
            cart_content = request.session[key]
            print(
                f"✅ Key '{key}': {cart_content} (items: {len(cart_content) if isinstance(cart_content, dict) else 'N/A'})")
        else:
            print(f"❌ Key '{key}': NO existe en sesión")

    print("--- Fin Debug ---\n")