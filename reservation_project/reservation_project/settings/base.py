"""
Settings base de TerraTokenX — compartido entre entornos.
Selección de entorno vía DJANGO_ENV (local | production).
"""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
import environ

env = environ.Env()

# BASE_DIR apunta a la raíz del proyecto (donde vive manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Variables de entorno desde .env para desarrollo local
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Valor de desarrollo. production.py rechaza el arranque si sigue siendo este.
SECRET_KEY_INSEGURA_DEFAULT = 'django-insecure-test-key-local-123'
SECRET_KEY = env('SECRET_KEY', default=SECRET_KEY_INSEGURA_DEFAULT)
DEBUG = env.bool('DEBUG', default=False)

# Hosts: configurables por entorno. En producción se validan (ver production.py).
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=[f'https://{h}' for h in ALLOWED_HOSTS if h not in ('127.0.0.1', 'localhost', '*')],
)

ADMIN_URL = env('ADMIN_URL', default='admin/')

# Application definition

INSTALLED_APPS = [
    'admin_interface',
    'colorfield',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'import_export',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_celery_beat',
    'django.contrib.humanize',
    'widget_tweaks',
    # Local
    'booking',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # CORS Middleware must be first
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'booking.middleware.KYCCheckMiddleware',
]

ROOT_URLCONF = 'reservation_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'booking', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'reservation_project.wsgi.application'

# Database — ruta persistente para SQLite local, DATABASE_URL en producción
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

DATABASES = {
    'default': dj_database_url.config(default=f"sqlite:///{DATA_DIR / 'db.sqlite3'}", conn_max_age=600)
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_L10N = True
USE_TZ = True

USE_THOUSAND_SEPARATOR = True
NUMBER_GROUPING = 3
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── DRF ──────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
        'login': '10/hour',
        'checkout': '20/hour',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ── JWT ──────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ── Celery / Redis ───────────────────────────────────────────────────────────
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Santiago'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'TIMEOUT': 300,
    }
}

# ── Reglas de negocio ────────────────────────────────────────────────────────
# Minutos que una reserva PENDIENTE retiene stock antes de liberarse.
# Debe superar el lifetime del invoice de Cryptomus (60 min).
RESERVA_PENDIENTE_TIMEOUT_MINUTOS = env.int('RESERVA_PENDIENTE_TIMEOUT_MINUTOS', default=90)

# ── Pasarelas de pago ────────────────────────────────────────────────────────
MERCADO_PAGO_PUBLIC_KEY = env('MERCADO_PAGO_PUBLIC_KEY', default='TEST_PUBLIC_KEY')
MERCADO_PAGO_ACCESS_TOKEN = env('MERCADO_PAGO_ACCESS_TOKEN', default='TEST_ACCESS_TOKEN')
MERCADOPAGO_WEBHOOK_SECRET = env('MERCADOPAGO_WEBHOOK_SECRET', default='')

CRYPTOMUS_MERCHANT_ID = env('CRYPTOMUS_MERCHANT_ID', default='')
CRYPTOMUS_PAYMENT_API_KEY = env('CRYPTOMUS_PAYMENT_API_KEY', default='')

KUSHKI_PUBLIC_KEY = env('KUSHKI_PUBLIC_KEY', default='')
KUSHKI_PRIVATE_KEY = env('KUSHKI_PRIVATE_KEY', default='')
KUSHKI_ENV = env('KUSHKI_ENV', default='sandbox')

# ── KYC / Registro Civil ─────────────────────────────────────────────────────
DIDIT_API_KEY = env('DIDIT_API_KEY', default='')
DIDIT_WEBHOOK_URL = env('DIDIT_WEBHOOK_URL', default='')
DIDIT_WEBHOOK_SECRET = env('DIDIT_WEBHOOK_SECRET', default='')

FLOID_API_KEY = env('FLOID_API_KEY', default='')

# ── Email (Resend) ───────────────────────────────────────────────────────────
RESEND_API_KEY = env('RESEND_API_KEY', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='contacto@terratokenx.com')
EMAIL_FROM = DEFAULT_FROM_EMAIL

# ── URLs base ────────────────────────────────────────────────────────────────
BASE_URL = env('BASE_URL', default='https://rwa.terratokenx.com')
FRONTEND_URL = env('FRONTEND_URL', default='https://rwa.terratokenx.com')

# --- URLs de Autenticación ---
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = '/'

# Configuración para archivos media (Imágenes subidas)
MEDIA_URL = '/media/'

# En Render, el disco persistente está montado en BASE_DIR / 'data'
if os.path.exists(os.path.join(BASE_DIR, 'data')):
    MEDIA_ROOT = os.path.join(BASE_DIR, 'data', 'media')
else:
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
