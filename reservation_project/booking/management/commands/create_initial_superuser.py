# reservation_project/booking/management/commands/create_initial_superuser.py

import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    """
    Crea un superusuario si no existe, usando variables de entorno.
    """
    help = 'Crea un superusuario inicial de forma no interactiva.'

    def handle(self, *args, **options):
        username = os.environ.get('SU_USERNAME')
        email = os.environ.get('SU_EMAIL')
        password = os.environ.get('SU_PASSWORD')

        if not all([username, email, password]):
            self.stdout.write(self.style.ERROR('Faltan las variables de entorno SU_USERNAME, SU_EMAIL o SU_PASSWORD.'))
            return

        if not User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(f'Creando superusuario: {username}'))
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS('Superusuario creado exitosamente.'))
        else:
            self.stdout.write(self.style.WARNING(f'El superusuario {username} ya existe.'))