import os
import django
from django.conf import settings

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from booking.models import Proyecto

def check_last_project():
    try:
        # Obtener el último proyecto
        proyecto = Proyecto.objects.last()
        if proyecto:
            print(f"Proyecto ID: {proyecto.id}")
            print(f"Nombre: {proyecto.nombre}")
            print(f"Tokens Totales: {proyecto.tokens_totales}")
            print(f"Tipo de dato: {type(proyecto.tokens_totales)}")
        else:
            print("No hay proyectos en la base de datos.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check_last_project()
