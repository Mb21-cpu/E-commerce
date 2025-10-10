from django import forms
from .models import Order

class CheckoutForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre'
        })
    )
    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellidos'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'tu@email.com'
        })
    )
    shipping_address = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Dirección completa de envío',
            'rows': 3
        })
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ciudad'
        })
    )
    postal_code = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Código Postal'
        })
    )
    country = forms.CharField(
        max_length=100,
        required=True,
        initial='España',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'País'
        })
    )

    class Meta:
        model = Order
        fields = [
            'first_name', 'last_name', 'email',
            'shipping_address', 'city', 'postal_code', 'country'
        ]