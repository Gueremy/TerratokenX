"""Settings de producción (Render).

Este módulo VALIDA su propia configuración al importarse. Si falta un secreto
crítico o la config es insegura, el proceso no arranca. Prefiere caída ruidosa
antes que un despliegue silenciosamente vulnerable.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import SECRET_KEY_INSEGURA_DEFAULT

DEBUG = False

# ── Validación de configuración crítica ──────────────────────────────────────

_errores = []

# 1. SECRET_KEY: sin ella, sesiones, JWT y tokens de reset son falsificables.
_generar = ('Generar con: python -c "from django.core.management.utils import '
            'get_random_secret_key; print(get_random_secret_key())"')
if not env('SECRET_KEY', default='') or SECRET_KEY == SECRET_KEY_INSEGURA_DEFAULT:
    _errores.append(f'SECRET_KEY no está definida (o usa el valor de desarrollo). {_generar}')
elif len(SECRET_KEY) < 50 or SECRET_KEY.startswith('django-insecure-'):
    _errores.append(
        f'SECRET_KEY es demasiado débil ({len(SECRET_KEY)} caracteres, mínimo 50). {_generar}'
    )

# 2. DATABASE_URL: sin ella se cae a SQLite, donde select_for_update() no
#    bloquea y reaparecen las race conditions de stock y créditos.
if not env('DATABASE_URL', default=''):
    _errores.append(
        'DATABASE_URL no está definida. En producción es obligatorio PostgreSQL: '
        'SQLite no soporta select_for_update() y permitiría sobreventa de stock.'
    )
elif DATABASES['default'].get('ENGINE', '').endswith('sqlite3'):
    _errores.append(
        'DATABASE_URL apunta a SQLite. En producción se requiere PostgreSQL.'
    )

# 3. ALLOWED_HOSTS: sin comodines.
if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
    _errores.append(
        'ALLOWED_HOSTS debe listar los dominios reales, sin comodín "*". '
        'Ej: ALLOWED_HOSTS=rwa.terratokenx.com,terratokenx.onrender.com'
    )

if _errores:
    raise ImproperlyConfigured(
        'Configuración de producción inválida:\n  - ' + '\n  - '.join(_errores)
    )

# ── Seguridad ────────────────────────────────────────────────────────────────

# URL del Admin oculta (definida en env o default seguro)
ADMIN_URL = env('ADMIN_URL', default='admin-seguro/')

# HTTPS y cookies seguras
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Render termina TLS

# CORS restringido en producción
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'https://terratokenx.onrender.com',
    'https://rwa.terratokenx.com',
])
CORS_ALLOW_CREDENTIALS = True

DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# ── Email ────────────────────────────────────────────────────────────────────
# Los envíos transaccionales usan la API de Resend (booking/integrations/resend.py),
# que exige RESEND_API_KEY en producción y falla ruidosamente si no está.
# Este backend cubre solo los send_mail() residuales de Django.
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')

if not env('RESEND_API_KEY', default=''):
    import warnings
    warnings.warn(
        'RESEND_API_KEY no está definida: los emails transaccionales fallarán. '
        'Configurarla en las variables de entorno de Render.',
        RuntimeWarning,
    )

# ── Logging estructurado a consola ───────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        }
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'default'},
    },
    'loggers': {
        'booking': {'level': 'INFO', 'handlers': ['console']},
        'booking.payments': {'level': 'WARNING', 'handlers': ['console']},
        'booking.kyc': {'level': 'INFO', 'handlers': ['console']},
        'booking.email': {'level': 'INFO', 'handlers': ['console']},
    },
}
