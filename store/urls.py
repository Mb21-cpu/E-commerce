from django.urls import path, include
from . import views

urlpatterns = [
    # --------------------
    # Vistas de Productos y Catálogo
    # --------------------
    path('', views.product_list_view, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/count/', views.get_cart_count_view, name='get_cart_count'),

    # --------------------
    # Vistas del Carrito
    # --------------------
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),

    # --------------------
    # Vistas de Compra y Historial
    # --------------------
    path('checkout/', views.checkout, name='checkout'),
    path('purchase_history/', views.purchase_history_view, name='purchase_history'),
    path('delete_purchase_history/', views.delete_purchase_history, name='delete_purchase_history'),

    # --------------------
    # Vistas de Autenticación
    # --------------------
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('password_reset/', views.password_reset_request, name='password_reset_request'),
    path('password_reset/done/', views.password_reset_done, name='password_reset_done'),
    path('password_reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password_reset/complete/', views.password_reset_complete, name='password_reset_complete'),
]