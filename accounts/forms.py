from django.contrib.auth.forms import UserCreationForm
from django import forms

class CustomUserCreationForm(UserCreationForm):
    """
    Formulario de creación de usuario personalizado que extiende el
    UserCreationForm de Django para incluir los campos 'email' y 'first_name'.
    """
    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
    )
    first_name = forms.CharField(
        label="Nombre",
        max_length=30,
        required=False,
    )

    class Meta(UserCreationForm.Meta):
        model = UserCreationForm.Meta.model
        fields = ("first_name", "email",) + UserCreationForm.Meta.fields