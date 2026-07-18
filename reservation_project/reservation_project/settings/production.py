"""Settings de producción (Render)."""

from .base import *  # noqa: F401,F403

DEBUG = False

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

# CORS restringido en producción
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'https://terratokenx.onrender.com',
    'https://rwa.terratokenx.com',
])
CORS_ALLOW_CREDENTIALS = True

DATABASES['default']['CONN_MAX_AGE'] = 60

# Email transaccional vía Resend (booking/integrations/resend.py).
# El backend SMTP de Django queda en consola: los envíos usan la API de Resend.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging estructurado a consola
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
