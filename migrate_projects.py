import os
import django
import sys

sys.path.append(r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from booking.models import Proyecto, Reserva, Configuracion

def migrate_data():
    # 1. Crear Proyecto Principal
    proyecto, created = Proyecto.objects.get_or_create(
        slug='refugio-patagonia',
        defaults={
            'nombre': 'Refugio Patagonia',
            'descripcion': 'Proyecto de inversión fraccionada en la Patagonia Chilena. Acceso a Laguna Plátano.',
            'precio_token': Configuracion.load().precio_base_token,
            'tokens_totales': 1500, # Valor manual o desde Config
            'rentabilidad_estimada': '12-18% Anual',
            'activo': True,
            'financiamiento_activo': True
        }
    )
    
    if created:
        print(f"✅ Proyecto creado: {proyecto.nombre}")
    else:
        print(f"ℹ️ Proyecto ya existe: {proyecto.nombre}")

    # 2. Migrar Reservas Huérfanas
    reservas = Reserva.objects.filter(proyecto__isnull=True)
    count = reservas.count()
    
    if count > 0:
        print(f"🔄 Migrando {count} reservas a {proyecto.nombre}...")
        reservas.update(proyecto=proyecto)
        print("✅ Migración completada.")
    else:
        print("ℹ️ No hay reservas pendientes de migración.")

if __name__ == '__main__':
    migrate_data()
