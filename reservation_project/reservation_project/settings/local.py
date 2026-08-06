"""
Settings para desarrollo local.
Uso: DJANGO_SETTINGS_MODULE=reservation_project.settings.local
"""
from .base import *  # noqa

DEBUG = True

ADMIN_URL = 'admin/'

# CORS permisivo solo en desarrollo
CORS_ALLOW_ALL_ORIGINS = True

# Email en consola durante desarrollo
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging verboso en desarrollo
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
