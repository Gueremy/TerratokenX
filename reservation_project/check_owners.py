import os
import django
import sys

# Configurar Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from django.contrib.auth.models import User
from booking.models import Proyecto

print("--- USUARIOS ---")
for u in User.objects.all():
    tipo = "SUPERUSER" if u.is_superuser else "Usuario Normal"
    print(f"ID: {u.id} | User: {u.username} | Email: {u.email} | Tipo: {tipo}")

print("\n--- PROYECTOS ---")
for p in Proyecto.objects.all():
    owner_str = f"{p.owner.username} (ID: {p.owner.id})" if p.owner else "NONE (Sin dueño)"
    print(f"ID: {p.id} | Proyecto: {p.nombre} | Owner Actual: {owner_str}")
