import time

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.views import LoginView
from .forms import CustomUserCreationForm, EmailAuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import AddressForm
from .models import Address
from django.http import HttpResponseRedirect
from django.urls import reverse


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Iniciar sesión automáticamente después del registro
            login(request, user)

            messages.success(request, f'¡Bienvenido, {user.first_name}! Tu cuenta ha sido creada.')
            return redirect('home')
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm  # Usamos nuestro formulario personalizado

    def form_valid(self, form):
        messages.success(self.request, f'Has iniciado sesión correctamente.')
        return super().form_valid(form)


def custom_logout(request):
    """Vista personalizada para cerrar sesión con mensaje - logout instantáneo"""
    if request.user.is_authenticated:
        user_name = request.user.first_name or request.user.username
        messages.success(request, f'¡Hasta pronto, {user_name}! Has cerrado sesión correctamente.')

    logout(request)
    return redirect('home')




def address_list(request):
    addresses = Address.objects.filter(user=request.user)

    # Evitar cache del navegador
    response = render(request, 'accounts/address_list.html', {'addresses': addresses})
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

@login_required
def address_create(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user

            # Si se marca como default, quitar default de otras direcciones
            if address.is_default:
                Address.objects.filter(user=request.user).update(is_default=False)

            address.save()
            return redirect('address_list')
    else:
        form = AddressForm()
    return render(request, 'accounts/address_form.html', {'form': form})


@login_required
def address_edit(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            address = form.save(commit=False)

            # Si se marca como default, quitar default de otras direcciones
            if address.is_default:
                Address.objects.filter(user=request.user).exclude(pk=pk).update(is_default=False)

            address.save()
            return redirect('address_list')
    else:
        form = AddressForm(instance=address)
    return render(request, 'accounts/address_form.html', {'form': form})


@login_required
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)

    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Dirección eliminada correctamente.')
        # Redirigir al nombre de la URL 'order_history' que existe en orders/urls.py
        return redirect('order_history')  # ← Este es el nombre correcto

    return render(request, 'accounts/address_confirm_delete.html', {'address': address})



'''@login_required
def user_dashboard(request):
    """Panel principal del usuario"""
    # Obtener últimos pedidos
    recent_orders = Order.objects.filter(customer=request.user).order_by('-created_at')[:5]

    # Obtener estadísticas (opcional)
    total_orders = Order.objects.filter(customer=request.user).count()
    total_spent = Order.objects.filter(customer=request.user).aggregate(
        total=models.Sum('total_paid')
    )['total'] or 0

    return render(request, 'accounts/dashboard.html', {
        'recent_orders': recent_orders,
        'total_orders': total_orders,
        'total_spent': total_spent,
    })'''