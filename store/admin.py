from django.contrib import admin
from .models import Product
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Order


@admin.action(description='Eliminar historial de compras')
def delete_purchase_history(modeladmin, request, queryset):
    for user in queryset:
        Order.objects.filter(user=user).delete()

    modeladmin.message_user(request, f"Se eliminó el historial de compras de {queryset.count()} usuario(s) exitosamente.")

class CustomUserAdmin(BaseUserAdmin):
    actions = [delete_purchase_history]

# Re-registra el modelo de usuario con tu clase de administración personalizada
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)



admin.site.register(Product)
