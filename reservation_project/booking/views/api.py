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



def api_stats(request):
    """
    API pública para obtener estadísticas de tokens vendidos/disponibles.
    Soporta ?project_id=X o ?slug=refugio-patagonia
    Si no se especifica, carga el proyecto por defecto (Refugio Patagonia).
    """
    from django.db.models import Sum
    from ..models import Proyecto
    
    project_id = request.GET.get('project_id')
    slug = request.GET.get('slug')
    
    try:
        if project_id:
            proyecto = Proyecto.objects.get(id=project_id)
        elif slug:
            proyecto = Proyecto.objects.get(slug=slug)
        else:
            # Default: Refugio Patagonia (o el primer activo)
            proyecto = Proyecto.objects.filter(activo=True).first()
            
        if not proyecto:
            return JsonResponse({'error': 'No active project found'}, status=404)

        tokens_totales = proyecto.tokens_totales
        precio_token = proyecto.precio_token
        
        # Sumar tokens de reservas CONFIRMADAS para este proyecto
        tokens_vendidos = proyecto.tokens_vendidos
        
        tokens_disponibles = proyecto.tokens_disponibles
        porcentaje_vendido = proyecto.porcentaje_vendido
        
        valor_proyecto = tokens_totales * precio_token
        monto_recaudado = tokens_vendidos * precio_token
        
        return JsonResponse({
            'project_name': proyecto.nombre,
            'tokens_totales': tokens_totales,
            'tokens_vendidos': tokens_vendidos,
            'tokens_disponibles': tokens_disponibles,
            'porcentaje_vendido': porcentaje_vendido,
            'precio_token_usd': precio_token,
            'valor_proyecto_usd': valor_proyecto,
            'monto_recaudado_usd': monto_recaudado,
        })
        
    except Proyecto.DoesNotExist:
        return JsonResponse({'error': 'Project not found'}, status=404)

def api_config(request):
    """
    API para obtener configuración (precio del token).
    Soporta ?project_id=X.
    """
    from ..models import Proyecto, Configuracion
    
    project_id = request.GET.get('project_id')
    slug = request.GET.get('slug')
    
    try:
        if project_id:
            proyecto = Proyecto.objects.get(id=project_id)
        elif slug:
            proyecto = Proyecto.objects.get(slug=slug)
        else:
            proyecto = Proyecto.objects.filter(activo=True).first()
            
        if proyecto:
            return JsonResponse({
                'precio_token_usd': proyecto.precio_token,
                'project_name': proyecto.nombre
            })
        else:
             # Fallback a configuración antigua o default
            config = Configuracion.load()
            return JsonResponse({
                'precio_token_usd': config.precio_base_token,
                'project_name': 'Default'
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_project_list(request):
    """
    API para obtener la lista de proyectos activos.
    Usada por index.html para generar el catálogo.
    """
    from ..models import Proyecto
    
    try:
        proyectos = Proyecto.objects.filter(activo=True).order_by('-created_at')
        data = []
        
        for p in proyectos:
            # Calcular porcentaje para mostrar barra pequeña en la card
            pct_vendido = p.porcentaje_vendido
            
            # Construir URL completa de la imagen
            # Prioridad: 1. Imagen subida (File), 2. URL externa
            img_url = ""
            if p.imagen_portada:
                img_url = request.build_absolute_uri(p.imagen_portada.url)
            elif p.imagen_portada_url:
                img_url = p.imagen_portada_url
            
            data.append({
                'id': p.id,
                'nombre': p.nombre,
                'slug': p.slug,
                'descripcion': p.descripcion[:100] + '...' if len(p.descripcion) > 100 else p.descripcion,
                'ubicacion': p.ubicacion,
                'precio_desde': p.precio_token,
                'imagen': img_url,
                'porcentaje_vendido': pct_vendido,
                'tokens_disponibles': p.tokens_disponibles,
                'estado': p.estado,  # Activo, Vendido, Proximamente
            })
            
        return JsonResponse({'projects': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_project_detail(request):
    """
    API para obtener detalles completos de un proyecto específico por slug.
    Usada por index2.html para llenar títulos, imágenes, etc.
    """
    from ..models import Proyecto
    
    slug = request.GET.get('slug')
    
    try:
        if not slug:
            return JsonResponse({'error': 'Slug is required'}, status=400)
            
        p = Proyecto.objects.get(slug=slug)
        
        # URL imagen
        # Prioridad: 1. Imagen subida (File), 2. URL externa
        img_url = ""
        if p.imagen_portada:
            img_url = request.build_absolute_uri(p.imagen_portada.url)
        elif p.imagen_portada_url:
             img_url = p.imagen_portada_url

        # Galería
        galeria = []
        for img in p.imagenes.all():
            url = ""
            if img.imagen:
                url = request.build_absolute_uri(img.imagen.url)
            elif img.imagen_url:
                url = img.imagen_url
            
            if url:
                galeria.append({
                    'url': url,
                    'caption': img.caption
                })
            
        # Secciones/Tabs del proyecto
        secciones = []
        for sec in p.secciones.filter(activo=True):
            secciones.append({
                'nombre': sec.nombre,
                'icono': sec.icono,
                'contenido': sec.contenido,
                'orden': sec.orden,
            })
            
        data = {
            'id': p.id,
            'nombre': p.nombre,
            'slug': p.slug,
            'descripcion': p.descripcion,
            'ubicacion': p.ubicacion,
            'rentabilidad_estimada': p.rentabilidad_estimada,
            'imagen': img_url,
            'precio_token_usd': p.precio_token,
            'pagina_oficial_url': p.pagina_oficial_url,
            'video_url': p.video_url,
            'tipo': p.tipo,
            'estado': p.estado,
            'galeria': galeria,
            'secciones': secciones,
        }
        return JsonResponse(data)
        
    except Proyecto.DoesNotExist:
        return JsonResponse({'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
