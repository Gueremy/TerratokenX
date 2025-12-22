# reservation_project/reservation_project/wsgi.py

import os
from django.core.wsgi import get_wsgi_application

# ¡ESTA ES LA LÍNEA CORRECTA Y DEFINITIVA!
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.reservation_project.settings')

application = get_wsgi_application()
