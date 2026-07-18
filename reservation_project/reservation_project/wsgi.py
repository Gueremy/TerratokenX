# reservation_project/reservation_project/wsgi.py

import os
from django.core.wsgi import get_wsgi_application

django_env = os.environ.get('DJANGO_ENV', 'production')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'reservation_project.settings.{django_env}')

application = get_wsgi_application()
