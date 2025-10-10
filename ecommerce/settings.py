import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-tu-clave-secreta-aqui'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_htmx',
    'accounts',
    'store',
    'orders',
    'cart',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'ecommerce.urls'

# CONFIGURACIÓN CORREGIDA - CAMBIA 'django.templates' por 'django.template'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',  # ← ESTA LÍNEA ES IMPORTANTE
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cart.context_processors.cart_item_count',
                'store.context_processors.categories',
                'ecommerce.context_processors.admin_dashboard',
            ],
        },
    },
]

# SOLO UNA CONFIGURACIÓN DE DATABASES - ELIMINA LA DUPLICADA
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
# Comenta temporalmente si la carpeta static no existe
# STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración de autenticación
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Configuración del carrito
CART_SESSION_ID = 'cart'

# Configuración de email (para desarrollo)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = 'mautodano2000@gmail.com'
EMAIL_HOST_PASSWORD = 'naeo cqnl lvug qfvj'
DEFAULT_FROM_EMAIL = 'mautodano2000@gmail.com'

ADMIN_EMAIL = 'mautodano2000@gmail.com'


STRIPE_PUBLISHABLE_KEY = 'pk_test_51SDolF3ElVeomltG9wFzIlcUo9RI89KxPuzj2MPsxDlIzPqMShOjwOYJ4Q3xlmdppnYR0ShFwzsHoKzzoUwcOC8Z00vw9OevDs'
STRIPE_SECRET_KEY = 'sk_test_51SDolF3ElVeomltG3CnOJsud9qu4on9E3BsJnFw7EA04dbCxglKuqk1dTmzRdvKknwRDN3Xisnq1aBIHqyUDAJb80059ZuqbO4'