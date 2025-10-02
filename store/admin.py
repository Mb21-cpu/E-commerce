from django.contrib import admin
# IMPORTANTE: Asegúrate de importar los modelos Category y Address de la app 'store'
from .models import Product, ContactMessage, Category, Address
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# Importa el modelo Order desde la app 'orders' (o donde lo tengas definido)
from orders.models import Order


# -------------------------------------
# NUEVO: Administración de Categorías (Sprint 2)
# -------------------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    # Autocompleta el slug al escribir el nombre
    prepopulated_fields = {'slug': ('name',)}


# -------------------------------------
# NUEVO: Administración de Direcciones (Sprint 2)
# -------------------------------------
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'customer', 'city', 'postal_code', 'is_default']
    list_filter = ['is_default', 'country', 'city']
    search_fields = ['full_name', 'street_address', 'postal_code']
    # Permite editar el estado predeterminado directamente desde la lista
    list_editable = ['is_default']


# -------------------------------------
# Acciones de Usuario
# -------------------------------------
@admin.action(description='Eliminar historial de compras')
def delete_purchase_history(modeladmin, request, queryset):
    """
    Acción de administración para eliminar todas las órdenes de los usuarios seleccionados.
    """
    for user in queryset:
        # CORRECCIÓN: Usar 'user' para filtrar las órdenes, ya que es el nombre del campo
        # en tu modelo Order: user = models.ForeignKey(User, ...)
        Order.objects.filter(user=user).delete()

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


# -------------------------------------
# Administración de Modelos de Tienda (Modificado)
# -------------------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # MODIFICACIÓN: 'category' añadido para que sea visible y editable
    list_display = ('name', 'category', 'price', 'stock', 'available')
    list_filter = ('available', 'category') # Permite filtrar por categoría
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