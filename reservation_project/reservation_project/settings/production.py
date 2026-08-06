"""
Settings para producción (Render).
Uso: DJANGO_SETTINGS_MODULE=reservation_project.settings.production
"""
from .base import *  # noqa
import environ

env = environ.Env()

DEBUG = False

# URL del admin oculta en producción
ADMIN_URL = env('ADMIN_URL', default='admin-seguro/')

# ─── CORS restringido en producción ──────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'https://terratokenx.onrender.com',
    'https://terratokenx-q7u4.onrender.com',
    'https://rwa.terratokenx.com',
]

# ─── HTTPS y cabeceras de seguridad ──────────────────────────────────────────
SECURE_SSL_REDIRECT          = True
SESSION_COOKIE_SECURE        = True
CSRF_COOKIE_SECURE           = True
SECURE_BROWSER_XSS_FILTER    = True
SECURE_CONTENT_TYPE_NOSNIFF  = True
X_FRAME_OPTIONS              = 'DENY'
SECURE_HSTS_SECONDS          = 31536000  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD          = True

# ─── Email via SendGrid ───────────────────────────────────────────────────────
EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'

# ─── Logging en producción ───────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'booking': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
