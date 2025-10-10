from .cart import Cart

def cart_item_count(request):
    """Context processor para obtener el conteo del carrito en todos los templates"""
    try:
        cart = Cart(request)
        return {
            'cart_item_count': cart.get_item_count()
        }
    except:
        return {'cart_item_count': 0}