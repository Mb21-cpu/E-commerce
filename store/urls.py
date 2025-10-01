from django.urls import path
from . import views

urlpatterns = [
    # Vistas de productos
    path('', views.product_list_view, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    # Vistas del carrito
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/count/', views.get_cart_count_view, name='get_cart_count'),
    path('cart/checkout/', views.checkout, name='checkout'),
    path('cart/update-cart/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),

    # Vistas de historial y gestión de compras
    path('purchase-history/', views.purchase_history_view, name='purchase_history'),
]