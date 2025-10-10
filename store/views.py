from django.db import models
from django.shortcuts import render, get_object_or_404,redirect
from django.views.generic import ListView, DetailView
from .models import Product, Category,Review
from django.db.models import Q
from orders.models import Order
from django.contrib import messages
from django.db.models import Avg
from django.contrib.auth.decorators import login_required


def home(request):
    """Vista para la página de inicio"""
    products = Product.objects.all()[:8]
    categories = Category.objects.all()[:6]
    return render(request, 'store/home.html', {
        'products': products,
        'categories': categories
    })


class ProductListView(ListView):
    model = Product
    template_name = 'store/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset()
        category_slug = self.kwargs.get('category_slug')

        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)

        return queryset.filter(available=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()

        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            context['current_category'] = get_object_or_404(Category, slug=category_slug)

        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'store/product_detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'slug'
    slug_field = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()

        # 🆕 OBTENER TODAS LAS IMÁGENES DEL PRODUCTO
        product = self.get_object()
        context['product_images'] = product.images.all()

        # Productos relacionados de la misma categoría
        if product.category:
            related_products = Product.objects.filter(
                category=product.category,
                available=True
            ).exclude(id=product.id)[:4]
            context['related_products'] = related_products

        # 🆕 NUEVO: SISTEMA DE RESEÑAS
        reviews = Review.objects.filter(product=product)
        average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

        # Verificar si el usuario ha comprado el producto
        user_has_purchased = False
        if self.request.user.is_authenticated:
            user_has_purchased = Order.objects.filter(
                customer=self.request.user,
                items__product=product,
                status='completed'  # Solo pedidos completados
            ).exists()

        context.update({
            'reviews': reviews,
            'average_rating': round(average_rating, 1),
            'user_has_purchased': user_has_purchased,
        })

        return context


@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Verificar que el usuario ha comprado el producto
    has_purchased = Order.objects.filter(
        customer=request.user,
        items__product=product,
        status='completed'  # Solo pedidos completados
    ).exists()

    if not has_purchased:
        messages.error(request, 'Solo puedes dejar reseñas de productos que has comprado.')
        return redirect('store:product_detail', slug=product.slug)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if not rating:
            messages.error(request, 'Por favor selecciona una calificación.')
            return redirect('product_detail', slug=product.slug)

        # Crear o actualizar la reseña
        review, created = Review.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={
                'rating': rating,
                'comment': comment
            }
        )

        if created:
            messages.success(request, '¡Tu reseña ha sido publicada!')
        else:
            messages.success(request, '¡Tu reseña ha sido actualizada!')

    return redirect('product_detail', slug=product.slug)

def product_search(request):
    query = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')
    products = Product.objects.filter(available=True)

    categories = Category.objects.all()
    selected_category = None

    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)

    if query:
        products = products.filter(
            models.Q(name__icontains=query) |
            models.Q(description__icontains=query)
        )

    return render(request, 'store/product_search.html', {
        'products': products,
        'query': query,
        'categories': categories,
        'selected_category': selected_category,
        'results_count': products.count()
    })


def product_list_by_category(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category, available=True)
    categories = Category.objects.all()

    return render(request, 'store/product_list.html', {
        'products': products,
        'categories': categories,
        'current_category': category
    })