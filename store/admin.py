from django.contrib import admin
from .models import Product, ContactMessage  # Importa ContactMessage aquí
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# Importa el modelo Order desde la app 'orders'
from orders.models import Order


@admin.action(description='Eliminar historial de compras')
def delete_purchase_history(modeladmin, request, queryset):
    """
    Acción de administración para eliminar todas las órdenes de los usuarios seleccionados.
    """
    for user in queryset:
        # Corrige el nombre del campo para que coincida con el modelo Order
        Order.objects.filter(customer=user).delete()

    modeladmin.message_user(
        request,
        f"Se eliminó el historial de compras de {queryset.count()} usuario(s) exitosamente."
    )


class CustomUserAdmin(BaseUserAdmin):
    """
    Personaliza la administración del modelo User.
    """
    actions = [delete_purchase_history]


# Re-registra el modelo de usuario con tu clase de administración personalizada
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Registra los modelos de tu tienda en el panel de administración
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'available')
    list_filter = ('available',)
    list_editable = ('price', 'stock', 'available')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    """
    Clase de administración para el modelo ContactMessage.
    Permite ver el mensaje completo y solo lectura de los campos.
    """
    list_display = ('name', 'email', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'message')
    # Los campos se marcan como solo lectura para que los mensajes no se modifiquen accidentalmente.
    readonly_fields = ('name', 'email', 'message', 'created_at')