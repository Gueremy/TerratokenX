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


def investor_login(request):
    """
    Vista de Login para Inversionistas.
    """
    if request.user.is_authenticated:
        return redirect('investor_dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"¡Bienvenido de nuevo, {username}!")
                return redirect('investor_dashboard')
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()

    return render(request, 'booking/investor/login.html', {'form': form})


def investor_register(request):
    """
    Vista de Registro rápido para Inversionistas.
    """
    if request.user.is_authenticated:
        return redirect('investor_dashboard')

    if request.method == 'POST':
        # Simple Registration Logic (Username = Email)
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'booking/investor/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Este correo ya está registrado.")
            return render(request, 'booking/investor/register.html')

        # Create User
        try:
            username = email.split('@')[0]
            # Ensure unique username
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1

            user = User.objects.create_user(username=username, email=email, password=password)
            user.first_name = nombre
            user.save()
            
            # Create UserProfile
            UserProfile.objects.create(user=user)

            login(request, user)
            messages.success(request, "Cuenta creada exitosamente. ¡Bienvenido!")
            return redirect('investor_dashboard')
        except Exception as e:
            messages.error(request, f"Error al crear cuenta: {e}")

    return render(request, 'booking/investor/register.html')


@login_required(login_url='investor_login')
def investor_profile(request):
    from ..models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.save()
        
        profile.rut = request.POST.get('rut')
        profile.telefono = request.POST.get('telefono')
        profile.direccion = request.POST.get('direccion')
        profile.metodo_certificacion = request.POST.get('metodo_certificacion', profile.METODO_FIRMA_VIRTUAL)
        profile.wallet_address = request.POST.get('wallet_address')
        profile.save()
        
        messages.success(request, "Perfil actualizado correctamente.")
        return redirect('investor_profile')
        
    return render(request, 'booking/investor/profile.html', {'profile': profile})


@login_required(login_url='investor_login')
def investor_kyc(request):
    from ..models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        if 'frontal' in request.FILES:
            profile.documento_identidad_frontal = request.FILES['frontal']
        if 'reverso' in request.FILES:
            profile.documento_identidad_reverso = request.FILES['reverso']
        if 'selfie' in request.FILES:
            profile.selfie_verificacion = request.FILES['selfie']
            
        profile.kyc_status = UserProfile.KYC_EN_REVISION
        profile.fecha_kyc = timezone.now()
        profile.save()
        
        messages.success(request, "Documentos enviados. Tu identidad está en proceso de verificación.")
        return redirect('investor_kyc')
        
    return render(request, 'booking/investor/kyc.html', {'profile': profile})


@login_required(login_url='investor_login')
def investor_dashboard(request):
    """
    Dashboard tipo ERP para el inversionista.
    Muestra resumen de capital, proyectos activos y documentos.
    """
    user = request.user
    
    # Obtener todas las reservas de este usuario (por email o FK user)
    # Priorizamos FK user si existe, sino fallback a email
    reservas = Reserva.objects.filter(user=user) | Reserva.objects.filter(correo=user.email)
    reservas = reservas.distinct().order_by('-created_at')

    # Calcular KPIs
    total_invertido = 0
    tokens_totales = 0
    proyectos_ids = set()
    
    for r in reservas:
        if r.estado_pago in [Reserva.ESTADO_CONFIRMADO, Reserva.ESTADO_EN_REVISION]:
            total_invertido += r.total
            tokens_totales += r.cantidad_tokens
            if r.proyecto:
                proyectos_ids.add(r.proyecto.id)

    cantidad_proyectos = len(proyectos_ids)
    
    # Plusvalía Estimada (Simulada hardcoded por ahora, luego puede venir del modelo Proyecto)
    plusvalia_estimada = int(total_invertido * 0.12) # 12% conservador

    context = {
        'reservas': reservas,
        'total_invertido': total_invertido,
        'tokens_totales': tokens_totales,
        'cantidad_proyectos': cantidad_proyectos,
        'plusvalia_estimada': plusvalia_estimada,
        'user': user
    }

    return render(request, 'booking/investor/dashboard.html', context)


@login_required(login_url='investor_login')
def investor_catalog(request):
    """
    Catálogo de proyectos protegido (Solo usuarios registrados).
    Separa proyectos Premium (INTERNAL) de Marketplace (EXTERNAL).
    Incluye info de Drops activos.
    """
    from booking.models import ProjectDrop
    now = timezone.now()
    
    proyectos_premium = Proyecto.objects.filter(
        activo=True, owner_type='INTERNAL'
    ).prefetch_related('drops').order_by('-created_at')
    
    proyectos_marketplace = Proyecto.objects.filter(
        activo=True, owner_type='EXTERNAL', compliance_status='APPROVED'
    ).prefetch_related('drops').order_by('-created_at')
    
    # Anotar drop activo en cada proyecto
    def anotar_drops(proyectos):
        for p in proyectos:
            p.drop_live = None
            p.drop_upcoming = None
            for d in p.drops.all():
                if d.activo and d.fecha_inicio <= now <= d.fecha_fin:
                    p.drop_live = d
                    break
                elif d.activo and now < d.fecha_inicio:
                    if p.drop_upcoming is None or d.fecha_inicio < p.drop_upcoming.fecha_inicio:
                        p.drop_upcoming = d
        return proyectos
    
    anotar_drops(proyectos_premium)
    anotar_drops(proyectos_marketplace)
    
    return render(request, 'booking/investor/catalog.html', {
        'proyectos_premium': proyectos_premium,
        'proyectos_marketplace': proyectos_marketplace,
        'user': request.user
    })



def marketplace_public(request):
    """
    Vista PÚBLICA del Marketplace (sin login requerido).
    Muestra todos los proyectos aprobados para atraer nuevos inversores.
    Incluye info de Drops activos.
    """
    from booking.models import ProjectDrop
    now = timezone.now()
    
    proyectos_premium = Proyecto.objects.filter(
        activo=True, owner_type='INTERNAL'
    ).prefetch_related('drops').order_by('-created_at')
    
    proyectos_marketplace = Proyecto.objects.filter(
        activo=True, owner_type='EXTERNAL', compliance_status='APPROVED'
    ).prefetch_related('drops').order_by('-created_at')
    
    # Anotar drop activo
    def anotar_drops(proyectos):
        for p in proyectos:
            p.drop_live = None
            p.drop_upcoming = None
            for d in p.drops.all():
                if d.activo and d.fecha_inicio <= now <= d.fecha_fin:
                    p.drop_live = d
                    break
                elif d.activo and now < d.fecha_inicio:
                    if p.drop_upcoming is None or d.fecha_inicio < p.drop_upcoming.fecha_inicio:
                        p.drop_upcoming = d
        return proyectos
    
    anotar_drops(proyectos_premium)
    anotar_drops(proyectos_marketplace)
    
    return render(request, 'booking/investor/marketplace.html', {
        'proyectos_premium': proyectos_premium,
        'proyectos_marketplace': proyectos_marketplace,
        'user': request.user if request.user.is_authenticated else None,
    })


@login_required(login_url='investor_login')
def investor_project_detail(request, slug):
    """
    Vista detallada del proyecto integrada totalmente en Django.
    Incluye proyectos relacionados (mismo tipo o aleatorios) y sistema de Drops.
    """
    proyecto = get_object_or_404(Proyecto, slug=slug)
    secciones = proyecto.secciones.filter(activo=True).order_by('orden')
    imagenes = proyecto.imagenes.all()
    documentos = proyecto.documentos.all()
    
    # ===== DROPS: Detectar drop activo o próximo =====
    from booking.models import ProjectDrop
    now = timezone.now()
    
    # Buscar drop EN VIVO (activo + dentro del rango de fechas)
    drop_activo = proyecto.drops.filter(
        activo=True,
        fecha_inicio__lte=now,
        fecha_fin__gte=now
    ).first()
    
    # Si no hay drop en vivo, buscar el PRÓXIMO
    drop_proximo = None
    if not drop_activo:
        drop_proximo = proyecto.drops.filter(
            activo=True,
            fecha_inicio__gt=now
        ).order_by('fecha_inicio').first()
    
    # Todos los drops del proyecto (para timeline)
    todos_drops = proyecto.drops.filter(activo=True).order_by('fecha_inicio')
    
    # Proyectos relacionados: mismo tipo primero, luego otros
    relacionados = list(
        Proyecto.objects.filter(
            activo=True, tipo=proyecto.tipo
        ).exclude(id=proyecto.id).order_by('?')[:6]
    )
    
    # Si no hay suficientes del mismo tipo, rellenar con otros
    if len(relacionados) < 6:
        faltan = 6 - len(relacionados)
        ids_excluir = [proyecto.id] + [p.id for p in relacionados]
        extras = Proyecto.objects.filter(
            activo=True
        ).exclude(id__in=ids_excluir).order_by('?')[:faltan]
        relacionados.extend(extras)

    context = {
        'proyecto': proyecto,
        'secciones': secciones,
        'imagenes': imagenes,
        'documentos': documentos,
        'relacionados': relacionados,
        'drop_activo': drop_activo,
        'drop_proximo': drop_proximo,
        'todos_drops': todos_drops,
        'user': request.user
    }
    return render(request, 'booking/investor/project_detail.html', context)


# ==================== FRACCIONADOR (KYB) & SELLER PANEL ====================
