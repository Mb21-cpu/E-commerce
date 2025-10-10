from django.contrib import admin
from .models import Address

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'city', 'postal_code', 'is_default', 'created_at']
    list_filter = ['city', 'country', 'is_default']
    search_fields = ['user__username', 'full_name', 'street_address']
    list_editable = ['is_default']