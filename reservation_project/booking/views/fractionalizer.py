from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from ..forms import ReservaForm, AdminReservaForm, ProyectoForm, ProyectoImagenFormSet
from ..models import Reserva, DiaFeriado, Coupon, Configuracion, Proyecto, ProjectDrop, UserProfile
from ..services.firmavirtual import FirmaVirtualService
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from datetime import datetime, timedelta, date
import os
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
import json
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from urllib.parse import urlencode
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction # Import transaction module
from google.oauth2 import service_account
from googleapiclient.discovery import build
import mercadopago
import logging


# Obtener una instancia del logger para registrar errores de forma más detallada
logger = logging.getLogger(__name__)

from .utils import create_google_calendar_link, add_event_to_spa_calendar, _get_filtered_reservas


@login_required(login_url='investor_login')
def fractionalizer_onboarding(request):
    """
    Vista para postulación de Fraccionadores (KYB).
    """
    from ..models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        profile.company_name = request.POST.get('company_name')
        profile.company_tax_id = request.POST.get('company_tax_id')
        profile.company_legal_rep = request.POST.get('company_legal_rep')
        
        if 'company_docs' in request.FILES:
            profile.company_docs = request.FILES['company_docs']
            
        # Cambiar estado
        profile.user_type = 'FRACTIONALIZER' 
        profile.kyb_status = 'REVIEW'
        profile.save()
        
        messages.success(request, "Solicitud enviada exitosamente. Revisaremos tu empresa en 48 horas.")
        return redirect('fractionalizer_dashboard')
        
    return render(request, 'booking/investor/fractionalizer_onboarding.html')


@login_required(login_url='investor_login')
def fractionalizer_dashboard(request):
    """
    Dashboard para vendedores (Fraccionadores).
    """
    from ..models import Proyecto
    
    # Solo mostrar proyectos de este usuario
    # Si es admin, mostrar TODOS para facilitar testing/gestión
    if request.user.is_superuser:
        proyectos = Proyecto.objects.all().order_by('-created_at')
    else:
        proyectos = Proyecto.objects.filter(owner=request.user)
    
    # Calcular KPIs para el dashboard
    total_proyectos = proyectos.count()
    total_tokens_vendidos = 0
    total_capital = 0
    
    # Iterar para sumar (lógica simple MVP)
    for p in proyectos:
        # Asumiendo que p.tokens_vendidos y precio base (100)
        # Si tokens_vendidos es property, esto funciona en Python
        vendidos = getattr(p, 'tokens_vendidos', 0)
        total_tokens_vendidos += vendidos
        total_capital += vendidos * 100 # Precio base HARDCODED por ahora (100 USD)
    
    from ..models import UserProfile
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.create(user=request.user)

    return render(request, 'booking/investor/fractionalizer_dashboard.html', {
        'proyectos': proyectos,
        'kpi': {
            'total_proyectos': total_proyectos,
            'tokens_vendidos': total_tokens_vendidos,
            'capital': total_capital
        },
        'user': request.user
    })



@login_required(login_url='investor_login')
def fractionalizer_create_project(request):
    """
    Vista (Wizard) para crear un nuevo proyecto.
    Requiere KYB aprobado.
    """
    from ..models import Proyecto, ProyectoImagen
    from django.utils.text import slugify
    
    # 1. Validar que sea fraccionador aprobado
    if not hasattr(request.user, 'profile') or request.user.profile.kyb_status != 'APPROVED':
        messages.error(request, "Debes tener tu cuenta de Fraccionador aprobada para crear proyectos.")
        return redirect('fractionalizer_dashboard')
        
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        ubicacion = request.POST.get('ubicacion')
        descripcion = request.POST.get('descripcion')
        tokens_totales = request.POST.get('tokens_totales', 1500)
        tipo = request.POST.get('tipo', 'Terreno')
        pagina_oficial_url = request.POST.get('pagina_oficial_url')
        video_url = request.POST.get('video_url')
        
        # Datos RWA para preservación y validación
        lat_raw = request.POST.get('gps_lat', '').replace(',', '.')
        lng_raw = request.POST.get('gps_lng', '').replace(',', '.')
        spv_name = request.POST.get('spv_legal_name', '')
        data_room = request.POST.get('data_room_url', '')

        # Contexto para preservar datos en caso de error
        form_data = {
            'nombre': nombre,
            'ubicacion': ubicacion,
            'descripcion': descripcion,
            'tokens_totales': tokens_totales,
            'tipo': tipo,
            'pagina_oficial_url': pagina_oficial_url,
            'video_url': video_url,
            'gps_lat': lat_raw,
            'gps_lng': lng_raw,
            'spv_legal_name': spv_name,
            'data_room_url': data_room,
            'imagen_portada_name': request.FILES['imagen_portada'].name if 'imagen_portada' in request.FILES else None,
            'archivo_propiedad_name': request.FILES['archivo_propiedad'].name if 'archivo_propiedad' in request.FILES else None
        }
        
        # 1. Validaciones básicas (Nombre y Ubicación)
        if not nombre or not ubicacion:
            messages.error(request, "Nombre y Ubicación son obligatorios.")
            return render(request, 'booking/investor/fractionalizer_create_project.html', {
                'form_data': form_data,
                'error_message': "Nombre y Ubicación son obligatorios."
            })

        # 2. Validación Archivo de Propiedad (Obligatorio)
        if 'archivo_propiedad' not in request.FILES:
            messages.error(request, "Es obligatorio subir la Escritura o Certificado de Dominio.")
            return render(request, 'booking/investor/fractionalizer_create_project.html', {
                'form_data': form_data,
                'error_message': "Es obligatorio subir la Escritura o Certificado de Dominio."
            })

        # 3. Validación GPS (Estricta: Rango y Formato)
        gps_lat_val = None
        gps_lng_val = None
        
        if lat_raw and lng_raw:
            try:
                lat_float = float(lat_raw)
                lng_float = float(lng_raw)

                # Validación de Rango de Seguridad (-90 a 90 / -180 a 180)
                if abs(lat_float) > 90:
                    return render(request, 'booking/investor/fractionalizer_create_project.html', {
                        'form_data': form_data,
                        'error_message': f"Latitud inválida ({lat_float}). Debe estar entre -90 y 90. Verifica el punto decimal."
                    })
                
                if abs(lng_float) > 180:
                     return render(request, 'booking/investor/fractionalizer_create_project.html', {
                        'form_data': form_data,
                        'error_message': f"Longitud inválida ({lng_float}). Debe estar entre -180 y 180. Verifica el punto decimal."
                    })

                gps_lat_val = lat_float
                gps_lng_val = lng_float
                
            except ValueError:
                return render(request, 'booking/investor/fractionalizer_create_project.html', {
                    'form_data': form_data,
                    'error_message': "Error en formato GPS. Usa números decimales con punto (ej: -41.32)."
                })

        # --- CREACIÓN DEL PROYECTO ---
        p = Proyecto()
        p.nombre = nombre
        p.ubicacion = ubicacion
        p.descripcion = descripcion
        try:
            p.tokens_totales = int(tokens_totales)
        except ValueError:
            p.tokens_totales = 1500
            
        p.tipo = tipo
        p.pagina_oficial_url = pagina_oficial_url
        p.video_url = video_url
        
        p.owner = request.user
        p.owner_type = 'EXTERNAL'
        p.compliance_status = 'REVIEW' # Nace en revisión
        p.docs_status = 'MISSING'
        
        # Slug único
        base_slug = slugify(nombre)
        p.slug = base_slug
        counter = 1
        while Proyecto.objects.filter(slug=p.slug).exists():
            p.slug = f"{base_slug}-{counter}"
            counter += 1
            
        # Asignar Archivo
        p.archivo_propiedad = request.FILES['archivo_propiedad']
            
        # Imagen Portada
        if 'imagen_portada' in request.FILES:
             p.imagen_portada = request.FILES['imagen_portada']
             
        # Asignar Metadata RWA
        if gps_lat_val is not None:
            p.gps_data = {'lat': gps_lat_val, 'lng': gps_lng_val}
        
        p.spv_legal_name = spv_name
        p.data_room_url = data_room

        p.save()
        
        # Procesar Galería de Imágenes (Dinámico)
        # Iteramos buscando inputs con nombre galeria_imagen_N, galeria_url_N, galeria_caption_N
        # Límite arbitrario de 20 imágenes para evitar bucles infinitos
        for i in range(20):
            key_file = f'galeria_imagen_{i}'
            key_url = f'galeria_url_{i}'
            key_caption = f'galeria_caption_{i}'
            
            file_data = request.FILES.get(key_file)
            url_data = request.POST.get(key_url)
            caption_data = request.POST.get(key_caption, '')
            
            # Si hay archivo O url, creamos la imagen
            if file_data or url_data:
                try:
                    img = ProyectoImagen(
                        proyecto=p,
                        imagen=file_data,
                        imagen_url=url_data,
                        caption=caption_data
                    )
                    img.save()
                    print(f"Imagen de galería {i} guardada para proyecto {p.nombre}")
                except Exception as e:
                    print(f"Error guardando imagen de galería {i}: {e}")
            
        messages.success(request, "¡Proyecto creado exitosamente! Ha sido enviado a revisión legal.")
        return redirect('fractionalizer_dashboard')
        
    return render(request, 'booking/investor/fractionalizer_create_project.html')


@login_required(login_url='investor_login')
def fractionalizer_edit_project(request, project_id):
    """
    Vista de edición para vendedores (Fractionalizers).
    Permite activar 'venta_solo_drops' y editar info básica.
    """
    from ..models import Proyecto
    from ..forms import FractionalizerProjectForm

    # Verificar propiedad y KYB
    proyecto = get_object_or_404(Proyecto, pk=project_id)
    if proyecto.owner != request.user:
        messages.error(request, "No tienes permiso para editar este proyecto.")
        return redirect('fractionalizer_dashboard')
        
    if request.method == 'POST':
        form = FractionalizerProjectForm(request.POST, request.FILES, instance=proyecto)
        if form.is_valid():
            p = form.save(commit=False)
            
            # --- RWA METADATA HANDLING ---
            # Guardar coordenadas GPS en formato JSON
            gps_lat = request.POST.get('gps_lat', '').replace(',', '.')
            gps_lng = request.POST.get('gps_lng', '').replace(',', '.')
            
            print(f"DEBUG: Intentando guardar GPS. Lat: '{gps_lat}', Lng: '{gps_lng}'")

            if gps_lat and gps_lng:
                try:
                    p.gps_data = {'lat': float(gps_lat), 'lng': float(gps_lng)}
                    print(f"DEBUG: GPS Data asignado al objeto: {p.gps_data}")
                except ValueError as e:
                    print(f"DEBUG: Error parseando GPS: {e}")
                    messages.warning(request, f"No se guardaron las coordenadas GPS porque el formato es inválido. Usa punto como decimal (ej: -41.32). Detalle: {e}")
                    pass 
            else:
                print("DEBUG: GPS Lat o Lng vacíos, no se actualiza gps_data.")
            
            # Guardar Datos Legales (permitir vaciar)
            # Nota: spv_legal_name y data_room_url ya son manejados por el form, 
            # pero esto asegura que si el usuario los vacía, se guarden vacíos
            # (aunque el form ya debería hacerlo si required=False).
            p.spv_legal_name = request.POST.get('spv_legal_name', '')
            p.data_room_url = request.POST.get('data_room_url', '')
                
            p.save()
            print(f"DEBUG: Proyecto guardado. ID: {p.id}")
            messages.success(request, f"Proyecto '{proyecto.nombre}' actualizado correctamente.")
            return redirect('fractionalizer_dashboard')
        else:
            messages.error(request, "Error al actualizar el proyecto. Revisa los campos.")
    else:
        form = FractionalizerProjectForm(instance=proyecto)
    
    # --- RWA GPS PRE-PROCESSING ---
    # Extraemos lat/lng explícitamente para evitar problemas de tipo en el template
    current_gps_lat = ''
    current_gps_lng = ''
    
    if proyecto.gps_data:
        if isinstance(proyecto.gps_data, dict):
            # Asegurar string y punto decimal
            current_gps_lat = str(proyecto.gps_data.get('lat', '')).replace(',', '.')
            current_gps_lng = str(proyecto.gps_data.get('lng', '')).replace(',', '.')
        elif isinstance(proyecto.gps_data, str):
            try:
                import json
                # Fix común para json guardado como repr() de python
                fixed_json = proyecto.gps_data.replace("'", '"')
                data = json.loads(fixed_json)
                current_gps_lat = str(data.get('lat', '')).replace(',', '.')
                current_gps_lng = str(data.get('lng', '')).replace(',', '.')
            except Exception as e:
                print(f"Error decoding GPS data for view: {e}")
                pass

    return render(request, 'booking/investor/fractionalizer_edit_project.html', {
        'form': form,
        'proyecto': proyecto,
        'current_gps_lat': current_gps_lat, # Variables explícitas para el template
        'current_gps_lng': current_gps_lng
    })
