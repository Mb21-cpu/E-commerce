from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/stripe/success/<int:order_id>/', views.stripe_payment_success, name='stripe_payment_success'),
    path('payment/simulation/<int:order_id>/', views.payment_simulation, name='payment_simulation'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path('history/', views.order_history, name='order_history'),
    path('detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('test-email/<int:order_id>/', views.test_email, name='test_email'),
]