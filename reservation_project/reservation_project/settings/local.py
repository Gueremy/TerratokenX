"""Settings de desarrollo local."""

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# Emails en consola — no se envía nada real
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS abierto solo en local
CORS_ALLOW_ALL_ORIGINS = True

# Sin Redis en local: caché en memoria y Celery en modo eager (síncrono)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 300,
    }
}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Estáticos sin manifest en local (evita errores con collectstatic sin correr)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
