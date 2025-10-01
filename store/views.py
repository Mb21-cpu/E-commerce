from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import views as auth_views
from django.views.generic import CreateView
from django.urls import reverse_lazy
import decimal

from .models import Product, Order, OrderItem


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
    }
    return render(request, 'store/product_list.html', context)


def product_detail(request, slug):
    """
    Muestra los detalles de un solo producto.
    """
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
# Vistas de Compra y Historial
# --------------------

@login_required
def checkout(request):
    """
    Procesa el carrito y crea una orden de compra.
    """
    cart = request.session.get('cart', {})

    if not cart:
        messages.error(request, "Tu carrito está vacío.")
        return redirect('product_list')

    order = Order.objects.create(user=request.user, is_paid=True)
    total_checkout_cost = decimal.Decimal(0)

    for product_id, item_data in cart.items():
        try:
            product = get_object_or_404(Product, id=product_id)
            item_price = decimal.Decimal(item_data['price'])
            item_quantity = item_data['quantity']

            if product.stock < item_quantity:
                messages.error(request,
                               f"Lo sentimos, no hay suficiente stock para {product.name}. Solo hay {product.stock} unidades disponibles.")
                order.delete()
                return redirect('cart_detail')

            product.stock -= item_quantity
            product.save()

            OrderItem.objects.create(
                order=order,
                product=product,
                price=item_price,
                quantity=item_quantity
            )

            total_checkout_cost += item_price * item_quantity

        except Product.DoesNotExist:
            messages.warning(request,
                             f"El producto {item_data['name']} ya no está disponible y no se añadió a la orden.")
            continue

    order.total_price = total_checkout_cost
    order.save()

    del request.session['cart']

    messages.success(request, "¡Gracias por tu compra! Tu pedido ha sido completado.")
    return redirect('purchase_history')


@login_required
def purchase_history_view(request):
    """
    Muestra el historial de compras del usuario autenticado.
    """
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
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
            Order.objects.filter(user_id=user_id).delete()
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