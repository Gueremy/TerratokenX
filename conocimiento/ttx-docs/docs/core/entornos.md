# Entornos — TerraTokenX

## Estructura de settings

```
terratokenx/settings/
├── base.py        ← todo lo compartido entre entornos
├── local.py       ← desarrollo: DEBUG=True, email console, DB local
└── production.py  ← Render: DEBUG=False, logging JSON, HTTPS
```

Selección de entorno via variable `DJANGO_ENV`:
```python
# manage.py / wsgi.py / asgi.py
import os
env = os.environ.get('DJANGO_ENV', 'local')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'terratokenx.settings.{env}')
```

---

## settings/base.py — config compartida

```python
from pathlib import Path
from decimal import Decimal
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_celery_beat',
    'storages',
    # Local
    'booking',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'booking.middleware.KYCCheckMiddleware',    # agregar Semana 3
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # En local: usar dj-database-url para parsear DATABASE_URL
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# JWT
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
}

# DRF
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

# Celery
CELERY_BROKER_URL = config('REDIS_URL')
CELERY_RESULT_BACKEND = config('REDIS_URL')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Santiago'

# Redis cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL'),
        'TIMEOUT': 300,
    }
}

# Cloudflare R2 (Storage)
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_S3_ENDPOINT_URL = config('R2_ENDPOINT_URL')
AWS_ACCESS_KEY_ID = config('R2_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('R2_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('R2_BUCKET_NAME')
AWS_S3_REGION_NAME = 'auto'
AWS_DEFAULT_ACL = 'private'
AWS_S3_FILE_OVERWRITE = False

# Pasarelas
MERCADOPAGO_ACCESS_TOKEN = config('MERCADOPAGO_ACCESS_TOKEN')
MERCADOPAGO_PUBLIC_KEY = config('MERCADOPAGO_PUBLIC_KEY')
MERCADOPAGO_WEBHOOK_SECRET = config('MERCADOPAGO_WEBHOOK_SECRET')

CRYPTOMUS_MERCHANT_ID = config('CRYPTOMUS_MERCHANT_ID')
CRYPTOMUS_PAYMENT_API_KEY = config('CRYPTOMUS_PAYMENT_API_KEY')

KUSHKI_PUBLIC_KEY = config('KUSHKI_PUBLIC_KEY')
KUSHKI_PRIVATE_KEY = config('KUSHKI_PRIVATE_KEY')
KUSHKI_ENV = config('KUSHKI_ENV', default='sandbox')

DIDIT_API_KEY = config('DIDIT_API_KEY')
DIDIT_WEBHOOK_URL = config('DIDIT_WEBHOOK_URL')
DIDIT_WEBHOOK_SECRET = config('DIDIT_WEBHOOK_SECRET')

FLOID_API_KEY = config('FLOID_API_KEY', default='')

RESEND_API_KEY = config('RESEND_API_KEY')
EMAIL_FROM = config('EMAIL_FROM', default='noreply@terratokenx.com')
```

---

## settings/local.py

```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

import dj_database_url
DATABASES['default'] = dj_database_url.parse(
    config('DATABASE_URL', default='postgresql://postgres:postgres@localhost:5432/terratokenx_dev')
)

# Email en consola — no envía emails reales
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

CORS_ALLOW_ALL_ORIGINS = True   # Solo en local

# No usar R2 en local — guardar archivos localmente
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
```

---

## settings/production.py

```python
from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

DEBUG = False

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# HTTPS
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Sentry
sentry_sdk.init(
    dsn=config('SENTRY_DSN', default=''),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False,
    environment='production',
)

# Logging JSON
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        }
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'json'},
    },
    'loggers': {
        'booking': {'level': 'INFO', 'handlers': ['console']},
        'booking.payments': {'level': 'WARNING', 'handlers': ['console']},
        'booking.blockchain': {'level': 'INFO', 'handlers': ['console']},
    },
}
```

---

## Disciplina de secretos

### Reglas absolutas

1. `.env` **NUNCA** va al repositorio. Está en `.gitignore`.
2. `.env.example` SÍ va al repositorio (sin valores reales).
3. La `BACKEND_WALLET_PRIVATE_KEY` (Fase 3) es el secreto más crítico. Si se filtra: alguien vacía el wallet de gas y puede comprometer contratos.
4. Para pasar credenciales al Dev Asociado: archivo `.env.frontend` compartido por canal cifrado (Signal, 1Password, Bitwarden). Nunca WhatsApp, nunca Slack público.

### Secretos por ambiente

| Variable | Local | Staging | Producción |
|----------|-------|---------|------------|
| `SECRET_KEY` | Cualquiera | Generado | Generado — diferente a staging |
| `DATABASE_URL` | Local DB | Render staging DB | Render prod DB |
| `MERCADOPAGO_ACCESS_TOKEN` | Token de TEST | Token de TEST | `APP_USR-...` real |
| `CRYPTOMUS_*` | Credenciales sandbox | Sandbox | Credenciales reales |
| `BACKEND_WALLET_PRIVATE_KEY` | Wallet de testnet | Wallet testnet Amoy | Wallet mainnet |

### Generar SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Checklist de deploy a producción

```
□ DEBUG=False verificado
□ SECRET_KEY diferente al de staging
□ ALLOWED_HOSTS incluye solo los dominios reales (sin *)
□ CORS_ALLOW_ALL_ORIGINS=False / CORS_ALLOWED_ORIGINS con dominios reales
□ Todas las variables de entorno configuradas en Render
□ Migraciones corridas: python manage.py migrate
□ Archivos estáticos: python manage.py collectstatic
□ Health check endpoint /health/ responde 200
□ Sentry configurado y recibiendo eventos de prueba
□ MP tokens son APP_USR-... (producción, no TEST)
□ Webhook URLs de MP y Cryptomus apuntan al dominio de producción
□ R2 bucket configurado y accesible
□ Redis conectado (Celery worker arranca sin errores)
□ manage.py check --deploy no reporta errores críticos
```
