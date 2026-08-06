"""
Settings base compartidos por todos los entornos.
No usar directamente — importar desde local.py o production.py.
"""
import os
from pathlib import Path
import environ
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Leer .env si existe (desarrollo local)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# ─── Seguridad ────────────────────────────────────────────────────────────────
SECRET_KEY = env('SECRET_KEY', default='django-insecure-test-key-local-123')

# ─── Hosts permitidos ─────────────────────────────────────────────────────────
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS = [
        f'https://{RENDER_EXTERNAL_HOSTNAME}',
        'https://terratokenx.onrender.com',
        'https://terratokenx-q7u4.onrender.com',
        'https://rwa.terratokenx.com',
    ]
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://terratokenx.onrender.com',
        'https://terratokenx-q7u4.onrender.com',
        'https://rwa.terratokenx.com',
    ]

ALLOWED_HOSTS += ['terratokenx-q7u4.onrender.com', 'rwa.terratokenx.com']

# ─── Apps instaladas ──────────────────────────────────────────────────────────
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
    'booking',
    'django.contrib.humanize',
    'widget_tweaks',
    'corsheaders',
]

# ─── Middleware ───────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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

# ─── Base de datos ────────────────────────────────────────────────────────────
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{DATA_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# ─── Validación de contraseñas ────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internacionalización ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_L10N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True
NUMBER_GROUPING = 3
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'

# ─── Archivos estáticos ───────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ─── Archivos media ───────────────────────────────────────────────────────────
MEDIA_URL = '/media/'
if os.path.exists(os.path.join(BASE_DIR, 'data')):
    MEDIA_ROOT = os.path.join(BASE_DIR, 'data', 'media')
else:
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ─── Clave primaria por defecto ───────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Autenticación ───────────────────────────────────────────────────────────
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = '/'

# ─── Servicios externos ───────────────────────────────────────────────────────
MERCADO_PAGO_PUBLIC_KEY  = env('MERCADO_PAGO_PUBLIC_KEY',  default='TEST_PUBLIC_KEY')
MERCADO_PAGO_ACCESS_TOKEN = env('MERCADO_PAGO_ACCESS_TOKEN', default='TEST_ACCESS_TOKEN')

SENDGRID_API_KEY = env('SENDGRID_API_KEY', default='SG.dummy-key-for-local-dev')
SENDGRID_SANDBOX_MODE_IN_DEBUG = False

CRYPTOMKT_API_KEY    = env('CRYPTOMKT_API_KEY',    default='')
CRYPTOMKT_API_SECRET = env('CRYPTOMKT_API_SECRET', default='')
CRYPTOMKT_WALLET_ETH  = env('CRYPTOMKT_WALLET_ETH',  default='0x498Ea2a861165362D0Ee55D9F3195B3e4FC68a73')
CRYPTOMKT_WALLET_BTC  = env('CRYPTOMKT_WALLET_BTC',  default='bc1ql4gja2w9ge27a28hhfcq0rx3m8z24m7sjl6a8d')
CRYPTOMKT_WALLET_USDT = env('CRYPTOMKT_WALLET_USDT', default='0x498Ea2a861165362D0Ee55D9F3195B3e4FC68a73')
CRYPTOMKT_WALLET_XLM  = env('CRYPTOMKT_WALLET_XLM',  default='')

DEFAULT_FROM_EMAIL     = env('DEFAULT_FROM_EMAIL',     default='contacto@terratokenx.com')
FIRMAVIRTUAL_BASE_URL  = env('FIRMAVIRTUAL_BASE_URL',  default='https://api.firmavirtual.legal')
FIRMAVIRTUAL_USER      = env('FIRMAVIRTUAL_USER',      default='')
FIRMAVIRTUAL_PASS      = env('FIRMAVIRTUAL_PASS',      default='')
FIRMAVIRTUAL_TEST_MODE = env.bool('FIRMAVIRTUAL_TEST_MODE', default=True)
TRAMIT_CALLBACK_URL    = env('TRAMIT_CALLBACK_URL',    default='https://rwa.terratokenx.com/webhooks/tramit-status/')
