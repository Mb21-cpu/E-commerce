# cart/urls.py - AGREGAR ESTA RUTA
from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('add-htmx/<int:product_id>/', views.add_to_cart_htmx, name='add_to_cart_htmx'),  # ← NUEVA
    path('remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('update/<int:product_id>/', views.cart_update, name='cart_update'),
    path('count/', views.cart_count, name='cart_count'),
    path('clear/', views.cart_clear, name='cart_clear'),
    path('icon/', views.cart_icon, name='cart_icon'),  # ← NUEVA
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
]