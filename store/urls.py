from django.urls import path
from . import views

urlpatterns = [
    # Rutas Generales
    path('', views.product_list_view, name='product_list'),
    path('contact/', views.contact_view, name='contact'),

    # Ruta de Detalle de Producto usando SLUG
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    # Rutas de Carrito
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/count/', views.get_cart_count_view, name='get_cart_count'),

    # Rutas de Checkout y Órdenes
    path('checkout/', views.checkout, name='checkout'),
    path('history/', views.purchase_history_view, name='purchase_history'),
    path('history/delete/', views.delete_purchase_history, name='delete_history'),

    path('order/<int:order_id>/', views.order_detail, name='order_detail'),

    # -----------------------------------------------------
    # RUTAS DE INTEGRACIÓN CON STRIPE (NUEVAS)
    # -----------------------------------------------------
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),

    # Ruta del Webhook (DEBE SER ACCESIBLE SIN CSRF)
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
]