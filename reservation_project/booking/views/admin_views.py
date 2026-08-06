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


@staff_member_required
def admin_panel(request):
    # --- Lógica para actualizar la configuración de precios ---
    if request.method == 'POST' and 'update_prices' in request.POST:
        config = Configuracion.load()
        # Usar .get() y limpiar el valor para evitar errores (ej: "35.000")
        precio_base_token_str = ''.join(filter(str.isdigit, request.POST.get('precio_base_token', '')))

        if precio_base_token_str:
            try:
                config.precio_base_token = int(precio_base_token_str)
                config.save()
                messages.success(request, "Precio del Token actualizado correctamente.")
            except (ValueError, TypeError):
                messages.error(request, "Por favor, ingresa un valor numérico válido.")
        else:
            messages.error(request, "El campo de precio es requerido.")
        
        # Redirigir a la misma página para prevenir reenvío del formulario
        return redirect('admin_panel')

    try:
        reservas_qs = _get_filtered_reservas(request)
        # Force evaluation to catch decimal errors early
        reservas = []
        for r in reservas_qs:
            try:
                # Force access to decimal fields to trigger any conversion errors
                _ = r.total
                reservas.append(r)
            except Exception:
                # Skip records with invalid decimal values
                pass
        
        dias_feriados = DiaFeriado.objects.all().order_by('fecha')
        coupons = Coupon.objects.all().order_by('-valid_to')
        config = Configuracion.load()  # Cargar configuración para mostrarla
        
        # Estadísticas de FirmaVirtual
        fv_stats = {
            'total': Reserva.objects.exclude(firmavirtual_id__isnull=True).exclude(firmavirtual_id='').count(),
            'pending': Reserva.objects.filter(firmavirtual_status='pending').exclude(firmavirtual_id__isnull=True).exclude(firmavirtual_id='').count(),
            'sent': Reserva.objects.filter(firmavirtual_status='sent').count(),
            'signed': Reserva.objects.filter(firmavirtual_status='signed').count(),
            'rejected': Reserva.objects.filter(firmavirtual_status='rejected').count(),
        }
        
        return render(request, 'booking/admin_panel_final.html', {
            'reservas': reservas,
            'dias_feriados': dias_feriados,
            'coupons': coupons,
            'config': config,  # Pasar el objeto de configuración a la plantilla
            'proyectos': Proyecto.objects.filter(activo=True),  # Para filtro por proyecto
            'request': request,
            'fv_stats': fv_stats,  # Estadísticas FirmaVirtual
        })
    except Exception as e:
        import traceback
        return HttpResponse(f"Error en admin_panel_v3 (CHECK TRACE): {e} | {traceback.format_exc()}", status=500)


@staff_member_required
def editar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    if request.method == 'POST':
        form = AdminReservaForm(request.POST, instance=reserva)
        if form.is_valid():
            form.save()
            return redirect('admin_sales')
    else:
        form = AdminReservaForm(instance=reserva)
    return render(request, 'booking/editar_reserva.html', {'form': form, 'reserva': reserva})


@staff_member_required
def eliminar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    if request.method == 'POST':
        reserva.delete()
        return redirect('admin_sales')
    # return render(request, 'booking/eliminar_reserva_clean.html', {'reserva': reserva})
    # Solución definitiva para evitar conflictos de OneDrive: Template en línea
    from django.template import Template, Context
    html_template = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Eliminar Compra de Token - TerraTokenX</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            tailwind.config = {
                theme: {
                    extend: {
                        colors: {
                            gold: { 400: '#E5C453', 500: '#D4AF37', 600: '#B5952F' },
                            dark: { 800: '#121212', 900: '#050505', 700: '#1e1e1e', card: '#1e1e1e' }
                        }
                    }
                }
            }
        </script>
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>body { font-family: 'Inter', sans-serif; }</style>
    </head>
    <body class="flex items-center justify-center min-h-screen p-4 text-gray-100" style="background: linear-gradient(to top right, #000000, #374151);">
        <main class="w-full max-w-lg">
            <div class="bg-dark-800 p-8 rounded-xl shadow-2xl border border-gray-800 text-center">
                <div class="text-red-500 mb-4"><span class="material-icons" style="font-size: 64px;">warning</span></div>
                <h1 class="text-2xl font-bold text-white mb-4">¿Eliminar Compra de Token?</h1>
                <div class="bg-red-900/20 border border-red-900/50 rounded-lg p-6 mb-8">
                    <p class="text-gray-300 text-lg leading-relaxed">
                        ¿Estás seguro que deseas eliminar la Compra de Token de <span class="font-bold text-white">{{ reserva.nombre }}</span> creada el <span class="font-bold text-white">{{ reserva.created_at|date:"d M Y" }}</span>?
                    </p>
                    <p class="text-red-400 text-sm mt-4 font-semibold">Esta acción no se puede deshacer.</p>
                </div>
                <form method="post" class="flex flex-col sm:flex-row gap-4">
                    {% csrf_token %}
                    <button type="submit" class="flex-1 flex justify-center items-center gap-2 bg-red-600 text-white font-bold py-3 px-6 rounded-lg hover:bg-red-700 shadow-lg shadow-red-900/20 transition-all transform hover:scale-[1.02]">
                        <span class="material-icons">delete_forever</span> Sí, Eliminar
                    </button>
                    <a href="/admin-panel/sales/" class="flex-1 flex justify-center items-center gap-2 bg-dark-700 text-gray-300 border border-gray-600 font-semibold py-3 px-6 rounded-lg hover:bg-gray-800 hover:text-white transition-colors">
                        <span class="material-icons">arrow_back</span> Cancelar
                    </a>
                </form>
            </div>
        </main>
    </body>
    </html>
    """
    from django.template import RequestContext
    return HttpResponse(Template(html_template).render(RequestContext(request, {'reserva': reserva})))



@staff_member_required
def agregar_feriado(request):
    if request.method == 'POST':
        fecha = request.POST.get('fecha')
        descripcion = request.POST.get('descripcion', '')
        if fecha:
            DiaFeriado.objects.get_or_create(fecha=fecha, defaults={'descripcion': descripcion})
    return redirect('admin_panel')


@staff_member_required
def eliminar_feriado(request, feriado_id):
    if request.method == 'POST':
        DiaFeriado.objects.filter(id=feriado_id).delete()
    return redirect('admin_panel')


@staff_member_required
def agregar_cupon(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        discount_percentage = request.POST.get('discount_percentage')
        valid_from = request.POST.get('valid_from')
        valid_to = request.POST.get('valid_to')

        if code and discount_percentage and valid_from and valid_to:
            try:
                Coupon.objects.create(
                    code=code,
                    discount_percentage=int(discount_percentage),
                    valid_from=valid_from,
                    valid_to=valid_to
                )
            except Exception as e:
                messages.error(request, f"Error al agregar cupón: {e}")
    return redirect('admin_panel')


@staff_member_required
def eliminar_cupon(request, coupon_id):
    if request.method == 'POST':
        Coupon.objects.filter(id=coupon_id).delete()
    return redirect('admin_panel')




@staff_member_required
def export_reservas_excel(request):
    """
    Genera un archivo Excel con las reservas.
    - Si es POST, exporta las reservas seleccionadas.
    - Si es GET, exporta las reservas filtradas.
    """
    reservas = _get_filtered_reservas(request)
    if not reservas.exists() and request.method == 'POST':
        messages.error(request, "No seleccionaste ninguna reserva para exportar.")
        return redirect('admin_panel')
    
    # Crear un libro de trabajo y una hoja
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Compras'

    # Escribir la cabecera
    headers = ['N° Compra', 'Nombre Cliente', 'Fecha Compra', 'Tokens', 'Total', 'Pagado', 'Correo', 'Teléfono', 'Proyecto']
    sheet.append(headers)

    # Escribir los datos de cada compra
    for reserva in reservas:
        sheet.append([
            reserva.numero_reserva,
            reserva.nombre,
            reserva.created_at.replace(tzinfo=None), # Excel no soporta tz-aware datetime a veces
            reserva.cantidad_tokens,
            reserva.total,
            'Sí' if reserva.pagado else 'No',
            reserva.correo,
            reserva.telefono,
            reserva.proyecto.nombre if reserva.proyecto else 'Sin Proyecto',
        ])

    # Crear la respuesta HTTP con nombre de archivo correcto
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    # Usar comillas y filename* para compatibilidad con todos los navegadores
    response['Content-Disposition'] = 'attachment; filename="inversiones_TerraTokenX.xlsx"; filename*=UTF-8\'\'inversiones_TerraTokenX.xlsx'
    workbook.save(response)
    
    return response


@staff_member_required
def export_reservas_pdf(request):
    """
    Genera un archivo PDF con una tabla de las reservas.
    - Si es POST, exporta las reservas seleccionadas.
    - Si es GET, exporta las reservas filtradas.
    """
    reservas = _get_filtered_reservas(request)
    if not reservas.exists() and request.method == 'POST':
        messages.error(request, "No seleccionaste ninguna reserva para exportar.")
        return redirect('admin_panel')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reservas.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Título del documento
    title = Paragraph("Reporte de Reservas", styles['h1'])
    elements.append(title)

    # Datos para la tabla
    data = [['N° Reserva', 'Cliente', 'Fecha', 'Total', 'Pagado']]
    for reserva in reservas:
        data.append([
            reserva.numero_reserva,
            reserva.nombre,
            reserva.created_at.strftime('%d-%m-%Y'),
            f"${reserva.total:,.0f}".replace(",", "."),
            'Sí' if reserva.pagado else 'No'
        ])

    # Crear y estilizar la tabla
    table = Table(data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 1.2*inch, 0.8*inch])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    elements.append(table)

    doc.build(elements)
    return response


@login_required # Assuming standard Django auth for admin panel
@user_passes_test(lambda u: u.is_superuser)
def admin_projects(request):
    """
    Vista para listar proyectos en el panel de administración.
    """
    from ..models import Proyecto
    proyectos = Proyecto.objects.all().order_by('-created_at')
    pending_count = Reserva.objects.filter(estado_pago='PENDIENTE').count()
    return render(request, 'booking/admin/projects.html', {
        'proyectos': proyectos,
        'active_tab': 'projects',
        'pending_count': pending_count,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_project_create(request):
    from ..forms import ProyectoForm
    if request.method == 'POST':
        form = ProyectoForm(request.POST, request.FILES)
        formset = ProyectoImagenFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            proyecto = form.save(commit=False)
            if not proyecto.owner:
                proyecto.owner = request.user
            proyecto.save()
            # Associate images with the newly created project
            images = formset.save(commit=False)
            for img in images:
                img.proyecto = proyecto
                img.save()
            # Handle deletions
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, 'Proyecto creado exitosamente.')
            return redirect('admin_projects')
        else:
            messages.error(request, 'Error al crear el proyecto. Por favor corrige los errores.')
    else:
        form = ProyectoForm()
        formset = ProyectoImagenFormSet()
    return render(request, 'booking/admin_project_form.html', {'form': form, 'formset': formset, 'title': 'Crear Proyecto'})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_project_edit(request, project_id):
    proyecto = get_object_or_404(Proyecto, pk=project_id)
    if request.method == 'POST':
        form = ProyectoForm(request.POST, request.FILES, instance=proyecto)
        formset = ProyectoImagenFormSet(request.POST, request.FILES, instance=proyecto)
        if form.is_valid() and formset.is_valid():
            form.save()
            images = formset.save(commit=False)
            for img in images:
                img.proyecto = proyecto
                img.save()
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, 'Proyecto actualizado exitosamente.')
            return redirect('admin_projects')
        else:
            messages.error(request, 'Error al actualizar el proyecto.')
    else:
        form = ProyectoForm(instance=proyecto)
        formset = ProyectoImagenFormSet(instance=proyecto)
    
    # Get sections and documents for this project
    secciones = proyecto.secciones.all()
    documentos = proyecto.documentos.all().order_by('-created_at')
    
    return render(request, 'booking/admin_project_form.html', {
        'form': form, 
        'formset': formset, 
        'title': 'Editar Proyecto', 
        'proyecto': proyecto,
        'secciones': secciones,
        'documentos': documentos,
    })

# ==================== CRUD DOCUMENTOS DE PROYECTO (DATA ROOM) ====================


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_documento_create(request, project_id):
    """Subir nuevo documento al Data Room de un proyecto"""
    from ..models import Proyecto, ProyectoDocumento
    
    proyecto = get_object_or_404(Proyecto, pk=project_id)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        archivo = request.FILES.get('archivo')
        es_publico = request.POST.get('es_publico') == 'on'
        requiere_nda = request.POST.get('requiere_nda') == 'on'
        
        if titulo and archivo:
            ProyectoDocumento.objects.create(
                proyecto=proyecto,
                titulo=titulo,
                archivo=archivo,
                es_publico=es_publico,
                requiere_nda=requiere_nda
            )
            messages.success(request, f'Documento "{titulo}" subido exitosamente.')
        else:
            messages.error(request, 'Título y archivo son requeridos.')
    
    return redirect('project_edit', project_id=project_id)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_documento_delete(request, doc_id):
    """Eliminar un documento del Data Room"""
    from ..models import ProyectoDocumento
    documento = get_object_or_404(ProyectoDocumento, pk=doc_id)
    project_id = documento.proyecto.id
    documento.delete()
    messages.success(request, 'Documento eliminado.')
    return redirect('project_edit', project_id=project_id)


# ==================== CRUD SECCIONES DE PROYECTO ====================


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_section_create(request, project_id):
    """Crear nueva sección para un proyecto"""
    from ..models import Proyecto, ProyectoSeccion
    
    proyecto = get_object_or_404(Proyecto, pk=project_id)
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        icono = request.POST.get('icono', '').strip()
        contenido = request.POST.get('contenido', '').strip()
        orden = request.POST.get('orden', 0)
        
        if nombre and contenido:
            ProyectoSeccion.objects.create(
                proyecto=proyecto,
                nombre=nombre,
                icono=icono if icono else None,
                contenido=contenido,
                orden=int(orden) if orden else 0,
                activo=True
            )
            messages.success(request, f'Sección "{nombre}" creada exitosamente.')
        else:
            messages.error(request, 'Nombre y contenido son requeridos.')
    
    return redirect('project_edit', project_id=project_id)



@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_section_edit(request, section_id):
    """Editar sección existente"""
    from ..models import ProyectoSeccion
    
    seccion = get_object_or_404(ProyectoSeccion, pk=section_id)
    
    if request.method == 'POST':
        seccion.nombre = request.POST.get('nombre', seccion.nombre).strip()
        seccion.icono = request.POST.get('icono', '').strip() or None
        seccion.contenido = request.POST.get('contenido', seccion.contenido).strip()
        seccion.orden = int(request.POST.get('orden', seccion.orden) or 0)
        seccion.activo = request.POST.get('activo') == 'on'
        seccion.save()
        messages.success(request, f'Sección "{seccion.nombre}" actualizada.')
    
    return redirect('project_edit', project_id=seccion.proyecto.id)



@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_section_delete(request, section_id):
    """Eliminar sección"""
    from ..models import ProyectoSeccion
    
    seccion = get_object_or_404(ProyectoSeccion, pk=section_id)
    project_id = seccion.proyecto.id
    nombre = seccion.nombre
    seccion.delete()
    messages.success(request, f'Sección "{nombre}" eliminada.')
    
    return redirect('project_edit', project_id=project_id)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_project_delete(request, project_id):
    from ..models import Proyecto
    
    proyecto = get_object_or_404(Proyecto, pk=project_id)
    # Optional: Don't hard delete, just deactivate? 
    # User asked for delete, let's hard delete but maybe with confirmation?
    # For simplicity in this step, direct delete as per standard admin flows or redirect to list
    
    # Actually, safest is usually a POST request but for a simple button we might use GET with caution or a specific confirmation page.
    # Let's assume the button sends a GET or we do a simple confirmation.
    
    proyecto.delete()
    messages.success(request, 'Proyecto eliminado correctamente.')
    return redirect('admin_projects')

# Import FirmaVirtual webhook from api_views
from ..api_views import firmavirtual_webhook, firmavirtual_status


@staff_member_required
def reenviar_contrato(request, reserva_id):
    """
    Vista para que el admin pueda reintentar manualmente el envío del contrato
    a FirmaVirtual si falló el primer intento automático.
    """
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    # Solo permitir envío si no se ha enviado ya o si fue rechazado/fallido
    # Permitimos reenvío si está 'sent' por si el email se perdió, pero avisamos.
    if reserva.firmavirtual_status == 'signed':
        messages.warning(request, f"El contrato ya está FIRMADO. No se puede re-enviar.")
        return redirect('admin_panel')
        
    fv_service = FirmaVirtualService()
    resultado = fv_service.create_contract_request(reserva)
    
    if "error" in resultado:
        messages.error(request, f"Error reenviando contrato: {resultado['error']}")
    else:
        # Éxito: Actualizar estado local
        reserva.firmavirtual_id = str(resultado.get('request_id'))
        # FirmaVirtual a veces retorna url, a veces no en v1/contract/clean
        # Si no la trae, no importa, llegará al correo del cliente.
        if resultado.get('url'):
            reserva.firmavirtual_url = resultado.get('url')
            
        reserva.firmavirtual_status = 'sent'
        reserva.save()
        messages.success(request, f"Contrato enviado correctamente a FirmaVirtual. ID: {reserva.firmavirtual_id}")
        
    return redirect('admin_panel')


# ============================================
# NUEVAS VISTAS DASHBOARD PROFESIONAL
# ============================================
from django.db.models import Sum


@staff_member_required
def admin_dashboard(request):
    """
    Vista principal del dashboard ERP con KPIs y resumen.
    """
    from django.db.models import Sum
    from django.db import models # Import models here to use models.Q
    
    # KPIs
    reservas_confirmadas = Reserva.objects.filter(estado_pago='CONFIRMADO')
    
    # Calcular ingresos: Cantidad de tokens × precio del token ($100)
    # Esto muestra el valor real de los tokens vendidos
    total_tokens = reservas_confirmadas.aggregate(total=Sum('cantidad_tokens'))['total'] or 0
    
    # Precio base del token (por proyecto o configuración global)
    # Para simplificar, usamos $100 como precio estándar
    PRECIO_TOKEN = 100
    total_revenue = total_tokens * PRECIO_TOKEN
    
    # Firmas
    signed_contracts = Reserva.objects.filter(firmavirtual_status='signed').count()
    pending_signatures = Reserva.objects.filter(
        firmavirtual_status__in=['sent', 'pending']
    ).exclude(firmavirtual_id__isnull=True).exclude(firmavirtual_id='').count()
    
    # Proyectos Activos
    projects_active = Proyecto.objects.filter(activo=True, estado='Activo').count()

    # KYB Pendientes
    from ..models import UserProfile
    pending_kyb_requests = UserProfile.objects.filter(kyb_status='REVIEW').count()
    
    # === TOP PROYECTOS (tokens × precio) ===
    top_projects = []
    PRECIO_TOKEN = 100
    
    # 1. Proyectos con ventas
    proyectos_activos = Proyecto.objects.filter(
        reserva_set__estado_pago='CONFIRMADO'
    ).distinct()
    
    for p in proyectos_activos:
        tokens_vendidos = Reserva.objects.filter(
            proyecto=p, estado_pago='CONFIRMADO'
        ).aggregate(total=Sum('cantidad_tokens'))['total'] or 0
        
        if tokens_vendidos > 0:
            top_projects.append({
                'nombre': p.nombre,
                'ubicacion': p.ubicacion,
                'tokens_vendidos': tokens_vendidos,
                'tokens_totales': p.tokens_totales,
                'porcentaje_vendido': p.porcentaje_vendido,
                'ingresos': tokens_vendidos * PRECIO_TOKEN,  # Tokens × $100
            })

    # 2. Ventas "Sin Proyecto" (Legacy / Huérfanos)
    orphaned_tokens = Reserva.objects.filter(
        estado_pago='CONFIRMADO', 
        proyecto__isnull=True
    ).aggregate(total=Sum('cantidad_tokens'))['total'] or 0
    
    if orphaned_tokens > 0:
        top_projects.append({
            'nombre': 'Ventas Directas / Otros',
            'ubicacion': 'General',
            'tokens_vendidos': orphaned_tokens,
            'tokens_totales': '-',
            'porcentaje_vendido': '-', 
            'ingresos': orphaned_tokens * PRECIO_TOKEN,
            'is_orphan': True # Flag por si queremos estilo diferente
        })
        
    # Re-ordenar final incluyendo huérfanos
    top_projects.sort(key=lambda x: x['ingresos'], reverse=True)
    
    # Actividad reciente
    recent_sales = Reserva.objects.order_by('-created_at')[:5]
    
    # Stats de firmas
    signatures_stats = {
        'total': Reserva.objects.exclude(firmavirtual_id__isnull=True).exclude(firmavirtual_id='').count(),
        'pending': Reserva.objects.filter(firmavirtual_status='pending').exclude(firmavirtual_id__isnull=True).count(),
        'sent': Reserva.objects.filter(firmavirtual_status='sent').count(),
        'signed': Reserva.objects.filter(firmavirtual_status='signed').count(),
        'rejected': Reserva.objects.filter(firmavirtual_status='rejected').count(),
    }
    
    # Pending count para sidebar
    pending_count = Reserva.objects.filter(estado_pago='PENDIENTE').count()
    
    context = {
        'active_tab': 'dashboard',
        'pending_count': pending_count,
        'kpi': {
            'total_revenue': total_revenue,  # Tokens × $100
            'tokens_sold': total_tokens,
            'signed_contracts': signed_contracts,
            'pending_signatures': pending_signatures,
            'projects_active': projects_active,
            'pending_kyb_requests': pending_kyb_requests,
        },
        'top_projects': top_projects,
        'recent_sales': recent_sales,
        'signatures_stats': signatures_stats,
    }
    
    return render(request, 'booking/admin/dashboard.html', context)



@staff_member_required
def admin_sales(request):
    """
    Vista de gestión de ventas/compras de tokens con paginación.
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    reservas_list = _get_filtered_reservas(request)
    pending_count = Reserva.objects.filter(estado_pago='PENDIENTE').count()
    
    # Paginación - 10 por página
    paginator = Paginator(reservas_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        reservas = paginator.page(page)
    except PageNotAnInteger:
        reservas = paginator.page(1)
    except EmptyPage:
        reservas = paginator.page(paginator.num_pages)
    
    context = {
        'active_tab': 'sales',
        'pending_count': pending_count,
        'reservas': reservas,
        'paginator': paginator,
    }
    
    return render(request, 'booking/admin/sales.html', context)



@staff_member_required
def admin_signatures(request):
    """
    Vista de gestión de firmas virtuales.
    """
    # Filtrar contratos con FirmaVirtual
    contratos = Reserva.objects.exclude(
        firmavirtual_id__isnull=True
    ).exclude(firmavirtual_id='').order_by('-updated_at')
    
    # Filtro por status
    status_filter = request.GET.get('status')
    if status_filter in ['sent', 'signed', 'rejected']:
        contratos = contratos.filter(firmavirtual_status=status_filter)
    
    # Stats
    stats = {
        'total': Reserva.objects.exclude(firmavirtual_id__isnull=True).exclude(firmavirtual_id='').count(),
        'sent': Reserva.objects.filter(firmavirtual_status='sent').count(),
        'signed': Reserva.objects.filter(firmavirtual_status='signed').count(),
        'rejected': Reserva.objects.filter(firmavirtual_status='rejected').count(),
    }
    
    pending_count = Reserva.objects.filter(estado_pago='PENDIENTE').count()
    
    context = {
        'active_tab': 'signatures',
        'pending_count': pending_count,
        'contratos': contratos,
        'stats': stats,
    }
    
    return render(request, 'booking/admin/signatures_v2.html', context)



@staff_member_required
def admin_coupons(request):
    """
    Vista de gestión de cupones de descuento.
    """
    from datetime import date
    
    coupons = Coupon.objects.all().order_by('-id')
    pending_count = Reserva.objects.filter(estado_pago='PENDIENTE').count()
    
    # Agregar conteo de uso a cada cupón
    for coupon in coupons:
        coupon.usage_count = Reserva.objects.filter(coupon=coupon).count()
    
    # Estadísticas
    today = date.today()
    stats = {
        'total': Coupon.objects.count(),
        'active': Coupon.objects.filter(is_active=True, valid_from__lte=today, valid_to__gte=today).count(),
        'used': Reserva.objects.filter(coupon__isnull=False).count(),
        'expired': Coupon.objects.filter(valid_to__lt=today).count(),
    }
    
    context = {
        'active_tab': 'coupons',
        'pending_count': pending_count,
        'coupons': coupons,
        'stats': stats,
    }
    
    return render(request, 'booking/admin/coupons.html', context)



@staff_member_required
def admin_coupon_create(request):
    """
    Crear un nuevo cupón.
    """
    if request.method == 'POST':
        code = request.POST.get('code', '').upper().strip()
        discount = request.POST.get('discount_percentage')
        valid_from = request.POST.get('valid_from')
        valid_to = request.POST.get('valid_to')
        is_active = request.POST.get('is_active') == 'on'
        
        if code and discount and valid_from and valid_to:
            Coupon.objects.create(
                code=code,
                discount_percentage=int(discount),
                valid_from=valid_from,
                valid_to=valid_to,
                is_active=is_active
            )
    
    return redirect('admin_coupons')



@staff_member_required
def admin_coupon_edit(request, coupon_id):
    """
    Editar un cupón existente.
    """
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':
        coupon.code = request.POST.get('code', '').upper().strip()
        coupon.discount_percentage = int(request.POST.get('discount_percentage', 0))
        coupon.valid_from = request.POST.get('valid_from')
        coupon.valid_to = request.POST.get('valid_to')
        coupon.is_active = request.POST.get('is_active') == 'on'
        coupon.save()
    
    return redirect('admin_coupons')



@staff_member_required
def admin_coupon_delete(request, coupon_id):
    """
    Eliminar un cupón.
    """
    if request.method == 'POST':
        coupon = get_object_or_404(Coupon, id=coupon_id)
        coupon.delete()
        messages.success(request, f'Cupón "{coupon.code}" eliminado correctamente.') 
    return redirect('admin_coupons') 

        
    
@staff_member_required
def admin_edit_user(request, user_id):
    """
    Editar datos básicos de un usuario (nombre, apellido, email) y Nivel KYC.
    """
    from ..models import UserProfile
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()
        
        # Actualizar Nivel KYC
        new_tier = request.POST.get('kyc_tier')
        if new_tier is not None:
            try:
                profile, _ = UserProfile.objects.get_or_create(user=user)
                old_tier = profile.kyc_tier
                profile.kyc_tier = int(new_tier)
                
                # Si se sube de nivel manualmente a > 0, asumimos que está verificado
                if int(new_tier) > 0 and profile.kyc_status != UserProfile.KYC_APROBADO:
                    profile.kyc_status = UserProfile.KYC_APROBADO
                
                # Si se baja a nivel 0, podríamos dejarlo como aprobado o no, pero mejor no tocar status si baja
                
                profile.save()
                
                if old_tier != int(new_tier):
                    messages.info(request, f"Nivel KYC actualizado de {old_tier} a {new_tier}.")
            except Exception as e:
                messages.error(request, f"Error actualizando perfil KYC: {e}")

        messages.success(request, f"Usuario {user.email} actualizado correctamente.")
        return redirect('admin_users')
    
    # Si es GET (aunque no se use si es por modal, pero por seguridad)
    return redirect('admin_users')


@staff_member_required
def admin_users(request):
    """
    Vista para gestionar usuarios (listado, bloqueo).
    """
    from django.db.models import Sum, Count, OuterRef, Subquery, Q
    from django.db.models.functions import Coalesce
    from ..models import Reserva

    # Subconsulta para obtener strings de proyectos por usuario
    # Como SQLite no tiene group_concat nativo fácil en subqueries de Django, calculamos sumas básicas
    # y los nombres los sacaremos en una propiedad o método si es necesario, 
    # pero para el listado usaremos anotaciones de suma.
    
    usuarios = User.objects.annotate(
        total_tokens=Coalesce(Sum('reserva_set__cantidad_tokens', filter=Q(reserva_set__estado_pago='CONFIRMADO')), 0),
        cantidad_proyectos=Count('reserva_set__proyecto', distinct=True, filter=Q(reserva_set__estado_pago='CONFIRMADO'))
    ).order_by('-date_joined')
    
        # Procesar filtros si es necesario (por email, nombre)
    
    # Agregar lista de proyectos manualmente para cada usuario (Evitar complejidad N+1 excesiva para listas pequeñas)
    for u in usuarios:
        if u.total_tokens > 0:
            u.proyectos_lista = ", ".join(Reserva.objects.filter(
                correo=u.email, 
                estado_pago='CONFIRMADO',
                proyecto__isnull=False
            ).values_list('proyecto__nombre', flat=True).distinct())
        else:
            u.proyectos_lista = "-"

    return render(request, 'booking/admin/users.html', {
        'usuarios': usuarios,
        'total_usuarios': usuarios.count(),
        'menu_active': 'users'
    })


@staff_member_required
def admin_kyc_list(request):
    """
    Lista de perfiles con su estado KYC para validación masiva.
    """
    from ..models import UserProfile
    perfiles = UserProfile.objects.all().order_by('-fecha_kyc')
    
    
    # Filtrar si es necesario
    status_filter = request.GET.get('status')
    if status_filter:
        perfiles = perfiles.filter(kyc_status=status_filter)
    
    # KYB Pendientes (Siempre mostrar si hay)
    kyb_profiles = UserProfile.objects.filter(kyb_status='REVIEW').order_by('-fecha_kyc')

    return render(request, 'booking/admin/kyc.html', {
        'perfiles': perfiles,
        'kyb_profiles': kyb_profiles,
        'menu_active': 'kyc',
        'status_filter': status_filter
    })


@staff_member_required
def admin_kyc_process(request, profile_id):
    """
    Aprobar o rechazar un KYC.
    """
    from ..models import UserProfile
    profile = get_object_or_404(UserProfile, id=profile_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '')
        
        if action == 'approve':
            profile.kyc_status = UserProfile.KYC_APROBADO
            # SUBIR DE NIVEL: Al aprobar documentos, pasa a Nivel 1 ($10k USD)
            profile.kyc_tier = 1 
            profile.comentarios_admin = ""
            messages.success(request, f"KYC de {profile.user.username} APROBADO. Nivel actualizado a 1 ($10k Límite).")
        elif action == 'reject':
            profile.kyc_status = UserProfile.KYC_RECHAZADO
            # BAJAR DE NIVEL: Si se rechaza, vuelve a básico
            profile.kyc_tier = 0
            profile.comentarios_admin = reason
            messages.warning(request, f"KYC de {profile.user.username} RECHAZADO: {reason}")
            
        profile.save()
        
    return redirect('admin_kyc_list')


@staff_member_required
def admin_kyb_process(request, profile_id):
    """
    Aprobar o rechazar un KYB (Fraccionador).
    """
    from ..models import UserProfile
    profile = get_object_or_404(UserProfile, id=profile_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            profile.kyb_status = 'APPROVED'
            profile.user_type = 'FRACTIONALIZER'
            messages.success(request, f"Fraccionador {profile.company_name} APROBADO.")
        elif action == 'reject':
            profile.kyb_status = 'REJECTED'
            messages.warning(request, f"Solicitud de {profile.company_name} RECHAZADA.")
            
        profile.save()
        
    return redirect('admin_kyc_list')


@staff_member_required
def admin_block_user(request, user_id):
    """
    Bloquear/Desbloquear un usuario.
    """
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        # Evitar bloquearse a sí mismo
        if user.id == request.user.id:
            messages.error(request, "No puedes bloquear tu propia cuenta.")
            return redirect('admin_users')
            
        # Toggle is_active
        user.is_active = not user.is_active
        user.save()
        
        status = "bloqueado" if not user.is_active else "activado"
        msg_type = messages.WARNING if not user.is_active else messages.SUCCESS
        messages.add_message(request, msg_type, f"Usuario {user.email} ha sido {status}.")
        
    return redirect('admin_users')

# Force reload 

# --- PORTAL INVERSIONISTA (Auth & Dashboard) ---
