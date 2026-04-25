
# Script para probar la vista fractionalizer_edit_project y el guardado de GPS
import os
import django
from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from booking.views import fractionalizer_edit_project
from booking.models import Proyecto

def setup_request(request):
    """Add session and message support to request"""
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    middleware = MessageMiddleware(lambda x: None)
    middleware.process_request(request)
    return request

# 1. Buscar un proyecto de prueba y su dueño
try:
    p = Proyecto.objects.first()
    if not p:
        print("No hay proyectos para probar.")
        exit()
        
    owner = p.owner
    if not owner:
        # Asignar al primer usuario si no tiene dueño
        owner = User.objects.first()
        p.owner = owner
        p.save()
        
    print(f"Probando con Proyecto ID {p.id}: {p.nombre} (Dueño: {owner.username})")
    
    # 2. Crear Request POST simulado CON GPS
    factory = RequestFactory()
    data = {
        'nombre': p.nombre,
        'descripcion': p.descripcion,
        'ubicacion': p.ubicacion,
        'tipo': p.tipo,
        'precio_token': p.precio_token,
        'tokens_totales': p.tokens_totales,
        'rentabilidad_estimada': p.rentabilidad_estimada,
        # DATOS QUE QUEREMOS PROBAR
        'gps_lat': '-45.50',
        'gps_lng': '-73.10',
        'spv_legal_name': 'Test SPV Updated',
        'data_room_url': 'https://example.com/dataroom',
        'financiamiento_activo': 'on' if p.financiamiento_activo else '',
        'venta_solo_drops': 'on' if p.venta_solo_drops else '',
    }
    
    request = factory.post(f'/portal/fractionalizer/edit/{p.id}/', data)
    request.user = owner
    setup_request(request)
    
    # 3. Ejecutar la vista
    print(">>> Ejecutando vista...")
    fractionalizer_edit_project(request, p.id)
    print(">>> Vista ejecutada.")
    
    # 4. Verificar si se guardó
    p.refresh_from_db()
    print(f"GPS Data en DB: {p.gps_data}")
    print(f"SPV Name en DB: {p.spv_legal_name}")
    
    if p.gps_data.get('lat') == -45.5 and p.gps_data.get('lng') == -73.1:
        print("SUCCESS: GPS guardado correctamente.")
    else:
        print("FAIL: GPS no coincide.")

except Exception as e:
    print(f"ERROR: {e}")
