from django.urls import path
from .views import ProductListView, ProductDetailView, home, product_search, add_review  # ← AÑADIR

urlpatterns = [
    path('', home, name='home'),
    path('products/', ProductListView.as_view(), name='product_list'),
    path('products/category/<slug:category_slug>/', ProductListView.as_view(), name='product_list_by_category'),
    path('product/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
    path('search/', product_search, name='product_search'),
    path('product/<int:product_id>/review/', add_review, name='add_review'),  # ← NUEVA
]
