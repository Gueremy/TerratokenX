import os, sys, django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from django.contrib.auth.models import User
from booking.models import Proyecto

# Obtener usuario ID 1 (Asumido como Admin Dios)
try:
    admin_god = User.objects.get(pk=1)
    print(f"Asignando proyectos al Admin Dios: {admin_god.username}")
    
    count = 0
    # Asignar TODOS los proyectos sin dueño al Admin Dios
    for p in Proyecto.objects.filter(owner__isnull=True):
        p.owner = admin_god
        p.save()
        print(f"Proyecto '{p.nombre}' asignado a {admin_god.username}")
        count += 1
    
    if count == 0:
        print("No había proyectos sin dueño.")
    else:
        print(f"\nTotal: {count} proyectos actualizados correctamente.")

except User.DoesNotExist:
    # Buscar cualquier superuser si el ID 1 falla
    admin_god = User.objects.filter(is_superuser=True).first()
    if admin_god:
        print(f"Usuario ID 1 no existe. Usando primer Superuser: {admin_god.username}")
        # Repetir logica
        count = 0
        for p in Proyecto.objects.filter(owner__isnull=True):
            p.owner = admin_god
            p.save()
            print(f"Proyecto '{p.nombre}' asignado a {admin_god.username}")
            count += 1
        print(f"\nTotal: {count} proyectos actualizados.")
    else:
        print("ERROR CRITICO: No hay ningun superusuario en la base de datos.")
