import os

from celery import Celery
from celery.schedules import crontab

django_env = os.environ.get('DJANGO_ENV', 'local')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'reservation_project.settings.{django_env}')

app = Celery('terratokenx')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Beat schedule — tareas periódicas (hora Chile, ver CELERY_TIMEZONE)
app.conf.beat_schedule = {
    'expirar-creditos-diario': {
        'task': 'booking.tasks.expirar_creditos_vencidos',
        'schedule': crontab(hour=2, minute=0),
    },
    'notificar-creditos-por-vencer': {
        'task': 'booking.tasks.notificar_creditos_por_vencer',
        'schedule': crontab(hour=9, minute=0),
    },
    'sync-tokens-vendidos': {
        'task': 'booking.tasks.sync_tokens_vendidos',
        'schedule': crontab(minute='*/15'),
    },
    'expirar-reservas-pendientes': {
        'task': 'booking.tasks.expirar_reservas_pendientes',
        'schedule': crontab(minute='*/15'),
    },
}
