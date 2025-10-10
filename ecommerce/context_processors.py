from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
from store.models import Product
from orders.models import Order


def admin_dashboard(request):
    """Context processor para el dashboard del admin"""

    # Solo procesar si estamos en el admin
    if not request.path.startswith('/admin/'):
        return {}

    # Fechas para filtros
    thirty_days_ago = timezone.now() - timedelta(days=30)
    seven_days_ago = timezone.now() - timedelta(days=7)

    # Métricas principales
    total_revenue = Order.objects.filter(
        created_at__gte=thirty_days_ago,
        status='completed'
    ).aggregate(total=Sum('total_paid'))['total'] or 0

    recent_orders_count = Order.objects.filter(
        created_at__gte=seven_days_ago
    ).count()

    active_products_count = Product.objects.filter(
        available=True,
        stock_quantity__gt=0
    ).count()

    low_stock_count = Product.objects.filter(
        stock_quantity__lte=5,  # Umbral de stock bajo
        stock_quantity__gt=0
    ).count()

    # Productos más vendidos
    top_products = Product.objects.filter(
        available=True
    ).annotate(
        total_sold=Count('orderitem')
    ).order_by('-total_sold')[:5]

    # Últimos pedidos
    recent_orders = Order.objects.all().order_by('-created_at')[:10]

    return {
        'total_revenue': total_revenue,
        'recent_orders_count': recent_orders_count,
        'active_products_count': active_products_count,
        'low_stock_count': low_stock_count,
        'top_products': top_products,
        'recent_orders': recent_orders,
    }