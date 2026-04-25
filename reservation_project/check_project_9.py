
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from booking.models import Proyecto

try:
    p = Proyecto.objects.get(pk=9)
    print(f"Proyecto: {p.nombre}")
    print(f"GPS Data Raw: {p.gps_data}")
    print(f"GPS Data Type: {type(p.gps_data)}")
    
    if isinstance(p.gps_data, str):
        print("ALERTA: gps_data es un STRING, no un dict. Esto rompe el template.")
        import json
        try:
            fixed_data = json.loads(p.gps_data.replace("'", '"')) # fix comillas simples de python dict string
            print(f"Intentando arreglar a: {fixed_data}")
            p.gps_data = fixed_data
            p.save()
            print("ARREGLADO: Ahora es un dict.")
        except Exception as e:
            print(f"No se pudo arreglar: {e}")

except Proyecto.DoesNotExist:
    print("Proyecto 9 no existe.")
