from django.shortcuts import render, redirect
from django.conf import settings  # Asegúrate de incluir este import
from django.contrib.auth import login,logout
from .forms import CustomUserCreationForm
from django.contrib.auth.views import LoginView

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)  # Usa la variable de settings
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})



class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

def logout_view(request):
    logout(request)
    return redirect(settings.LOGIN_REDIRECT_URL)