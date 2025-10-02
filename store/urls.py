from django.urls import path
from . import views

urlpatterns = [
    # 1. RUTA PRINCIPAL (DEBE IR PRIMERO)
    path('', views.product_list, name='product_list'),

    # -----------------------------------------------------
    # 2. RUTAS FIJAS DE ALTO NIVEL (DEBEN IR ANTES DE <slug:>)
    # -----------------------------------------------------
    path('contact/', views.contact_view, name='contact'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('checkout/', views.checkout, name='checkout'),
    path('history/', views.purchase_history_view, name='purchase_history'),  # YA NO ESTÁ BLOQUEADA

    # RUTAS DE ACCIONES (Dentro de sus prefijos)
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/count/', views.get_cart_count_view, name='get_cart_count'),

    path('history/delete/', views.delete_purchase_history, name='delete_history'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),

    # RUTAS DE INTEGRACIÓN CON STRIPE
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),

    # -----------------------------------------------------
    # 3. RUTAS CON SLUG/ID (DEBEN IR ÚLTIMAS)
    # -----------------------------------------------------
    # El detalle del producto tiene un prefijo fijo 'product/', por lo que no causa conflicto
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    # La ruta genérica de categoría (slug) DEBE ir al final de la sección principal
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),
]
