from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from store.models import Product
from .cart import Cart
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponse, JsonResponse
from orders.models import Coupon

def cart_add(request, product_id):
    """Añadir producto al carrito (vista normal con redirect)"""
    product = get_object_or_404(Product, id=product_id)
    cart = Cart(request)

    # Determinar cantidad y URL de redirección
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        redirect_url = request.POST.get('redirect_url', request.META.get('HTTP_REFERER', 'product_list'))
    else:
        quantity = int(request.GET.get('quantity', 1))
        redirect_url = request.GET.get('redirect_url', request.META.get('HTTP_REFERER', 'product_list'))

    # Añadir al carrito usando la clase Cart
    added = cart.add(product, quantity)

    if added:
        messages.success(request, f'✅ {product.name} añadido al carrito')
    else:
        messages.error(request, f'❌ No se pudo añadir {product.name} - Stock insuficiente')

    return redirect(redirect_url)


@require_POST
def add_to_cart_htmx(request, product_id):
    """Vista HTMX para añadir al carrito SIN recargar página"""
    product = get_object_or_404(Product, id=product_id)
    cart = Cart(request)

    # Añadir al carrito usando la clase Cart
    added = cart.add(product)

    if added:
        cart_count = cart.get_item_count()
        # Devolver solo el fragmento HTML actualizado
        return HttpResponse(f'''
            <span id="cart-count" class="cart-count {"has-items" if cart_count > 0 else "empty"}">
                {cart_count}
            </span>
            <script>
                // Mostrar notificación toast
                showToast('✅ {product.name} añadido al carrito', 'success');

                // Animación del contador
                const cartCount = document.getElementById('cart-count');
                if (cartCount) {{
                    cartCount.style.transform = 'scale(1.3)';
                    setTimeout(() => {{
                        cartCount.style.transform = 'scale(1)';
                    }}, 300);
                }}

                // Actualizar botones del producto si es necesario
                const productButtons = document.querySelectorAll('[data-product-id="{product.id}"]');
                productButtons.forEach(btn => {{
                    if (btn.classList.contains('cart-add-btn')) {{
                        btn.innerHTML = '✅ Añadido';
                        btn.disabled = true;
                        setTimeout(() => {{
                            btn.innerHTML = '🛒 Añadir al Carrito';
                            btn.disabled = false;
                        }}, 2000);
                    }}
                }});
            </script>
        ''')
    else:
        return HttpResponse(f'''
            <script>
                showToast('❌ No se puede añadir {product.name} - Stock insuficiente', 'error');

                // Feedback visual en el botón
                const productButtons = document.querySelectorAll('[data-product-id="{product.id}"]');
                productButtons.forEach(btn => {{
                    if (btn.classList.contains('cart-add-btn')) {{
                        const originalHTML = btn.innerHTML;
                        btn.innerHTML = '❌ Sin Stock';
                        btn.disabled = true;
                        setTimeout(() => {{
                            btn.innerHTML = originalHTML;
                            btn.disabled = false;
                        }}, 2000);
                    }}
                }});
            </script>
        ''', status=400)

def cart_remove(request, product_id):
    """Remover producto del carrito"""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    messages.success(request, f"🗑️ '{product.name}' removido del carrito")
    return redirect('cart_detail')


def cart_detail(request):
    """Vista detalle del carrito"""
    cart = Cart(request)

    # DEBUG
    print(f"🔍 cart_detail - Carrito tiene {cart.get_item_count()} items")
    print(f"🔍 cart_detail - Session cart: {request.session.get('cart', {})}")

    cart_items = list(cart)
    available_items = [item for item in cart_items if item.get('available', False)]

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'available_items': available_items,
        'available_count': len(available_items),
        'total_count': len(cart_items),
    }

    # ✅ Si el carrito está vacío después de un pago, mostrar mensaje especial
    if len(cart_items) == 0 and any(
            'completado' in msg.message or 'éxito' in msg.message for msg in messages.get_messages(request)):
        print("✅ Carrito vacío después de pago exitoso")

    return render(request, 'cart/detail.html', context)


def cart_update(request, product_id):
    """Actualizar cantidad en carrito con validación de stock"""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))

    # VERIFICAR STOCK ANTES DE ACTUALIZAR
    if not product.can_add_to_cart(quantity):
        messages.error(request,
                       f"❌ Stock insuficiente. Disponible: {product.stock_quantity}"
                       )
        return redirect('cart_detail')

    success = cart.add(product=product, quantity=quantity, override_quantity=True)

    if success:
        messages.success(request, f"✅ Cantidad actualizada para '{product.name}'")
    else:
        messages.error(request, f"❌ No se pudo actualizar '{product.name}'")

    return redirect('cart_detail')


@require_GET
def cart_count(request):
    """
    Vista simple para obtener el conteo del carrito (API para HTMX)
    """
    try:
        cart = Cart(request)
        total_items = cart.get_item_count()
        return JsonResponse({'count': total_items})
    except Exception as e:
        print(f"❌ Error en cart_count: {e}")
        return JsonResponse({'count': 0})


def cart_clear(request):
    """Limpiar todo el carrito"""
    cart = Cart(request)
    cart.clear()
    messages.success(request, "🗑️ Carrito limpiado")
    return redirect('cart_detail')


# Vista para obtener el ícono del carrito actualizado (para HTMX)
@require_GET
def cart_icon(request):
    """Devolver solo el ícono del carrito actualizado"""
    cart = Cart(request)
    cart_count = cart.get_item_count()

    return render(request, 'partials/cart_icon.html', {
        'cart_count': cart_count
    })


@require_POST
def apply_coupon(request):
    coupon_code = request.POST.get('coupon_code', '').strip().upper()
    cart = Cart(request)

    if cart.is_empty():
        messages.error(request, 'Tu carrito está vacío')
    else:
        success, coupon = cart.apply_coupon(coupon_code)
        if success:
            messages.success(request, f'¡Cupón {coupon.code} aplicado correctamente!')
        else:
            messages.error(request, 'El código introducido no es válido o está inactivo')

    return redirect('cart_detail')


@require_POST
def remove_coupon(request):
    cart = Cart(request)
    cart.remove_coupon()
    messages.success(request, 'Cupón removido correctamente')
    return redirect('cart_detail')