from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from .forms import ReservaForm, AdminReservaForm, ProyectoForm, ProyectoImagenFormSet
from .models import Reserva, DiaFeriado, Coupon, Configuracion, Proyecto, ProjectDrop, UserProfile
from .services.firmavirtual import FirmaVirtualService
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

def create_google_calendar_link(reserva):
    """Genera un enlace para agregar la reserva al Calendario de Google."""
    # Desactivado para tokens
    return "#"

def landing_page(request):
    """
    Renderiza la nueva Landing Page Premium (index.html).
    """
    return render(request, 'booking/landing_premium.html')

def add_event_to_spa_calendar(reserva):
    """
    Agrega un evento al calendario central del negocio usando una cuenta de servicio.
    """
    # Desactivado para tokens
    pass

def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None and user.is_staff:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Acceso denegado. Solo para administradores.")
        else:
            messages.error(request, "Nombre de usuario o contraseña inválidos.")
    else:
        form = AuthenticationForm()
    return render(request, 'booking/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('reservation_form')

def create_mp_preference(request, reserva_id):
    """
    Crea una preferencia de pago en Mercado Pago (Checkout Pro) y redirige al usuario.
    """
    reserva = get_object_or_404(Reserva, id=reserva_id)
    if reserva.pagado:
        messages.info(request, "Esta reserva ya ha sido pagada.")
        return redirect('reservation_success', reserva_id=reserva.id)

    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

    # Define las URLs a las que Mercado Pago redirigirá al usuario.
    # `build_absolute_uri` es crucial para que funcione en producción.
    back_urls = {
        "success": request.build_absolute_uri(reverse('reservation_success', args=[reserva.id])),
        "failure": request.build_absolute_uri(reverse('reservation_form')), # Vuelve al formulario si falla
        "pending": request.build_absolute_uri(reverse('reservation_success', args=[reserva.id])), # También a éxito, pero con estado pendiente
    }

    preference_data = {
        "items": [
            {
                "title": f"Reserva Inversión TerraTokenX - {reserva.numero_reserva}",
                "quantity": 1,
                "unit_price": float(reserva.total),
                "currency_id": "USD",  # USD para clientes internacionales
            }
        ],
        "payer": {
            "name": reserva.nombre,
            "email": reserva.correo,
        },
        "back_urls": back_urls,
        "auto_return": "approved", # Redirige automáticamente solo si el pago es aprobado
        "external_reference": str(reserva.id), # ID de tu reserva para identificarla después
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        # Redirigir al usuario a la URL de pago de Mercado Pago
        return redirect(preference["init_point"])
    except Exception as e:
        # Mensaje amigable para el administrador/cliente
        logger.error(f"Error Mercado Pago: {e}")
        messages.error(request, "Error de Configuración: La API Key de Mercado Pago parece haber expirado o es inválida. Revise sus credenciales.")
        return redirect('reservation_form')

def _get_filtered_reservas(request):
    """
    Función auxiliar para obtener un queryset de reservas filtrado
    basado en los parámetros GET o POST.
    """
    if request.method == 'POST' and 'selected_ids' in request.POST:
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            return Reserva.objects.none() # Devuelve un queryset vacío si no hay IDs
        return Reserva.objects.filter(id__in=selected_ids).order_by('-fecha')
    
    # Filtros para GET
    reservas = Reserva.objects.all()
    estado_pago = request.GET.get('estado_pago')
    metodo_pago = request.GET.get('metodo_pago')
    proyecto_id = request.GET.get('proyecto')

    if estado_pago in ['PENDIENTE', 'EN_REVISION', 'CONFIRMADO']:
        reservas = reservas.filter(estado_pago=estado_pago)
    
    if metodo_pago in ['MP', 'CRYPTO', 'CRYPTO_MANUAL']:
        reservas = reservas.filter(metodo_pago=metodo_pago)
    
    if proyecto_id:
        reservas = reservas.filter(proyecto_id=proyecto_id)
    
    return reservas.order_by('-created_at')

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

@login_required
def reservation_form(request):
    print("DEBUG: CARGANDO VISTA reservation_form (v2)")
    from .models import Proyecto, Reserva, Configuracion, ProjectDrop, UserProfile
    
    # 1. Detectar Proyecto desde Slug (opcional)
    project_slug = request.GET.get('project_slug') or request.GET.get('slug')
    proyecto_seleccionado = None
    if project_slug:
        # Solo permitir proyectos que estén activos y disponibles
        proyecto_seleccionado = Proyecto.objects.filter(slug=project_slug, activo=True, estado='Activo').first()
        if not proyecto_seleccionado and project_slug:
            # Si el slug es inválido o el proyecto no está activo, redirigir al catálogo o mostrar error
            messages.warning(request, "El proyecto solicitado no está disponible actualmente.")
            return redirect('reservation_form')

    # Obtener lista de proyectos activos para el selector
    proyectos_activos = Proyecto.objects.filter(activo=True, estado='Activo')
    
    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            reserva = form.save(commit=False)
            
            # 1. Asignar Cupón si existe
            if 'coupon_code' in form.cleaned_data and form.cleaned_data['coupon_code']:
                reserva.coupon = form.cleaned_data['coupon_code']
            
            # 2. Proyecto Fallback
            if not reserva.proyecto and proyecto_seleccionado:
                reserva.proyecto = proyecto_seleccionado
            
            # 3. Validación de Stock y Disponibilidad
            if not reserva.proyecto or not reserva.proyecto.activo or reserva.proyecto.estado != 'Activo':
                form.add_error('proyecto', "El proyecto seleccionado no es válido o no está activo.")
            elif reserva.cantidad_tokens > reserva.proyecto.tokens_disponibles:
                form.add_error('cantidad_tokens', f"Lo sentimos, solo quedan {reserva.proyecto.tokens_disponibles} tokens.")
            else:
                # 4. Sistema de Drops Completo
                from booking.models import ProjectDrop
                now = timezone.now()
                drop_activo = reserva.proyecto.drops.filter(
                    activo=True,
                    fecha_inicio__lte=now,
                    fecha_fin__gte=now
                ).first()
                
                drop_error = False
                
                # ── CERROJO: Si el proyecto exige Drops, bloquear sin Drop activo ──
                if reserva.proyecto.venta_solo_drops and not drop_activo:
                    # Verificar si hay un próximo Drop programado
                    proximo_drop = reserva.proyecto.drops.filter(
                        activo=True,
                        fecha_inicio__gt=now
                    ).order_by('fecha_inicio').first()
                    
                    if proximo_drop:
                        form.add_error(None, f"⏳ La venta está cerrada. Próximo Drop: {proximo_drop.nombre} — abre el {proximo_drop.fecha_inicio.strftime('%d/%m/%Y %H:%M')}.")
                    else:
                        form.add_error(None, "🔒 La venta está cerrada. No hay Drops programados. Sigue nuestras redes para enterarte del próximo lanzamiento.")
                    drop_error = True
                
                if drop_activo and not drop_error:
                    # ── STOCK DEL DROP (Corrección DR-03) ──
                    # Calculamos el stock real disponible en este drop
                    stock_real_drop = drop_activo.tokens_disponibles_drop - drop_activo.tokens_vendidos_drop
                    
                    if reserva.cantidad_tokens > stock_real_drop:
                        if stock_real_drop <= 0:
                            form.add_error('cantidad_tokens', "¡Los tokens de este Drop se han agotado! Espera el próximo Drop.")
                        else:
                            form.add_error('cantidad_tokens', f"Solo quedan {stock_real_drop} tokens en este Drop.")
                        drop_error = True
                    
                    # ── ANTI-BALLENA: Límite por usuario en este Drop ──
                    if not drop_error and drop_activo.max_tokens_por_usuario and request.user.is_authenticated:
                        tokens_ya_comprados = Reserva.objects.filter(
                            drop=drop_activo,
                            user=request.user,
                            estado_pago__in=['PENDIENTE', 'EN_REVISION', 'CONFIRMADO']
                        ).aggregate(total=models.Sum('cantidad_tokens'))['total'] or 0
                        
                        tokens_disponibles_usuario = drop_activo.max_tokens_por_usuario - tokens_ya_comprados
                        
                        if reserva.cantidad_tokens > tokens_disponibles_usuario:
                            if tokens_disponibles_usuario <= 0:
                                form.add_error('cantidad_tokens', f"🐋 Ya alcanzaste el máximo de {drop_activo.max_tokens_por_usuario} tokens por persona en este Drop.")
                            else:
                                form.add_error('cantidad_tokens', f"🐋 Solo puedes comprar {tokens_disponibles_usuario} tokens más en este Drop (límite: {drop_activo.max_tokens_por_usuario} por persona).")
                            drop_error = True
                    
                    # ── PRECIO DEL DROP Y TOTAL (Corrección DR-04) ──
                    if not drop_error:
                         # Si hay precio override, lo usamos para el cálculo del total
                         precio_final = drop_activo.precio_override if drop_activo.precio_override else reserva.proyecto.precio_token
                         
                         # Forzamos el total aquí para asegurar que se cobre lo correcto
                         reserva.total = reserva.cantidad_tokens * precio_final
                         
                         # Vinculamos el Drop
                         reserva.drop = drop_activo

                # ── KYC CHECK / LIMITES DE INVERSION (GLOBAL - SIEMPRE SE EJECUTA) ──
                if not drop_error and request.user.is_authenticated:
                    try:
                        # Obtener perfil (asegurar existencia)
                        profile, _ = UserProfile.objects.get_or_create(user=request.user)
                        
                        # Calcular monto estimado de esta compra usando el total ya calculado o base
                        # Si no hay drop activo o error, usamos precio base
                        if hasattr(reserva, 'total') and reserva.total > 0:
                             monto_estimado_usd = float(reserva.total)
                        else:
                             monto_estimado_usd = float(reserva.cantidad_tokens) * float(reserva.proyecto.precio_token)
                        
                        # DEBUG
                        print(f"🔍 KYC DEBUG: User={request.user.username} | Tier={profile.kyc_tier} | Limit Restante=${profile.remaining_limit} | Compra=${monto_estimado_usd}")
                        
                        # Verificar límite restante del usuario
                        limite_restante = float(profile.remaining_limit)
                        
                        if monto_estimado_usd > limite_restante:
                            tier_display = profile.get_kyc_tier_display()
                            msg = f"⛔ BLOQUEO KYC: Vas a comprar ${monto_estimado_usd:,.0f} USD, pero tu límite disponible es de ${limite_restante:,.0f} USD ({tier_display}). Verifícate para aumentar tu cupo."
                            print(f"🚫 BLOCKED: {msg}")
                            form.add_error(None, msg)
                            drop_error = True
                            
                    except Exception as e:
                        print(f"❌ CRITICAL KYC ERROR: {e}")
                        # FAIL-CLOSED: Si falla el chequeo, bloqueamos por seguridad
                        form.add_error(None, f"Error técnico verificando perfil de inversor. Intente nuevamente. ({e})")
                        drop_error = True
                
                if not drop_error:
                    # Todo OK - Guardamos
                    metodo_pago = request.POST.get('metodo_pago', 'MP')
                    reserva.metodo_pago = metodo_pago
                    
                    # Si no se calculó total arriba (ej: compra normal sin drop), calcularlo ahora
                    if not reserva.total:
                        reserva.total = reserva.cantidad_tokens * reserva.proyecto.precio_token
                        
                    reserva.save()
                    
                    # Actualizar tokens vendidos del Drop
                    if drop_activo:
                        drop_activo.tokens_vendidos_drop += reserva.cantidad_tokens
                        drop_activo.save(update_fields=['tokens_vendidos_drop'])
                    
                    # Log con detalles del monto calculado
                    with open('debug_form.log', 'a', encoding='utf-8') as f:
                        drop_info = f", Drop: {drop_activo.nombre}" if drop_activo else ""
                        f.write(f"[{datetime.now()}] Reserva OK #{reserva.id}: {reserva.cantidad_tokens} tokens, Total: ${reserva.total}, Cupón: {reserva.coupon}{drop_info}\n")
                    
                    # Enviar email...
                    import threading
                    def send_email_async(res_id):
                        try:
                            r = Reserva.objects.get(id=res_id)
                            subject = 'Tu solicitud de reserva - TerraTokenX'
                            template = 'booking/email/pending_reservation_mp.html'
                            if r.metodo_pago == 'CRYPTO':
                                subject = '⏳ Instrucciones para finalizar tu inversión'
                                template = 'booking/email/pending_reservation_crypto.html'
                            html_msg = render_to_string(template, {'reserva': r})
                            send_mail(subject, '', settings.DEFAULT_FROM_EMAIL, [r.correo], html_message=html_msg)
                        except: pass
                    threading.Thread(target=send_email_async, args=(reserva.id,)).start()

                    if reserva.metodo_pago == 'CRYPTO':
                        return crear_orden_cryptomarket(request, reserva)
                    return redirect('create_mp_preference', reserva_id=reserva.id)

        # Si llegamos aquí con error
        with open('debug_form.log', 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] ERROR FORM: {form.errors.as_json()}\n")
            
        return render(request, 'booking/reservation_form_v2.html', {
            'form': form,
            'proyectos_activos': proyectos_activos,
            'proyecto': proyecto_seleccionado or proyectos_activos.first(),
            'error_active': True
        })
    else:
        initial_data = {}
        if proyecto_seleccionado:
            initial_data['proyecto'] = proyecto_seleccionado
        form = ReservaForm(initial=initial_data)

    # --- Contexto para la validación del lado del cliente (JavaScript) ---
    config = Configuracion.load()
    
    # Obtener solo proyectos activos
    proyectos_activos_qs = Proyecto.objects.filter(activo=True, estado='Activo')
    
    # Construir data enriquecida para JS (Manejo de Drops y Stock)
    import json
    proyectos_js_list = []
    now = timezone.now()
    
    for p in proyectos_activos_qs:
        # Lógica de Drop para el Frontend
        drop_activo = p.drops.filter(activo=True, fecha_inicio__lte=now, fecha_fin__gte=now).first()
        
        # Precio
        precio_real = drop_activo.precio_override if (drop_activo and drop_activo.precio_override) else p.precio_token
        
        # Stock
        stock_real = p.tokens_disponibles # Stock general
        if drop_activo:
             stock_drop = drop_activo.tokens_disponibles_drop - drop_activo.tokens_vendidos_drop
             # El stock disponible es el del Drop, acotado por el total real del proyecto si fuese menor
             stock_real = stock_drop 
             
             # Anti-whale check simple para frontend (opcional, por ahora stock global del drop)
             if drop_activo.max_tokens_por_usuario:
                  # Nota: Para saber cuánto le queda al user específico habría que filtrar por user, 
                  # pero para el selector general usamos el stock del drop.
                  pass

        proyectos_js_list.append({
            'id': p.id,
            'nombre': p.nombre,
            'precio': precio_real,
            'rentabilidad': p.rentabilidad_estimada,
            'imagen': p.imagen_portada_url if p.imagen_portada_url else (p.imagen_portada.url if p.imagen_portada else ''),
            'stock': stock_real if stock_real > 0 else 0
        })
    
    proyectos_js_data = json.dumps(proyectos_js_list)

    # Determinar precio a mostrar (Proyecto específico o Configuración Global)
    precio_actual = proyecto_seleccionado.precio_token if proyecto_seleccionado else config.precio_base_token

    # DATOS KYC PARA EL FRONTEND
    kyc_info = {
        'remaining_usd': 500, # Default Nivel 0
        'limit_usd': 500,
        'tier_label': 'Nivel 0 (Básico)',
        'is_authenticated': request.user.is_authenticated
    }
    
    if request.user.is_authenticated:
        try:
            # Asegurar importación aquí por si acaso
            from .models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            kyc_info['remaining_usd'] = float(profile.remaining_limit)
            kyc_info['limit_usd'] = float(profile.limit_usd)
            kyc_info['tier_label'] = profile.get_kyc_tier_display()
        except Exception as e:
            print(f"Error cargando KYC info para frontend: {e}")

    return render(request, 'booking/reservation_form_v2.html', {
        'form': form,
        'config': config,
        'precio_base_token': precio_actual, # Contexto dinámico
        'proyecto': proyecto_seleccionado,  # Contexto del proyecto
        'proyectos_activos': proyectos_activos_qs, # Lista para selector Django puro
        'proyectos_js_data': proyectos_js_data, # JSON para AlpineJS
        'kyc_info': kyc_info, # Info para JS
    })


def reservation_success(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    payment_status = request.GET.get('status')
    pago_procesado_ahora = False
    
    # Se procesa el pago solo una vez para evitar duplicados si el usuario recarga la página.
    if payment_status == 'approved' and not reserva.pagado:
        # 1. Actualiza la base de datos de forma atómica y segura.
        with transaction.atomic():
            # Recargamos la reserva dentro de la transacción para evitar race conditions.
            reserva_a_pagar = Reserva.objects.select_for_update().get(id=reserva_id)
            if not reserva_a_pagar.pagado:
                reserva_a_pagar.pagado = True
                reserva_a_pagar.save()
                pago_procesado_ahora = True
    elif payment_status == 'manual_review':
        # No auto-confirmamos, pero podemos registrar algo si es necesario.
        # El estado ya fue puesto en EN_REVISION por la API 'api_manual_confirm_payment'
        pass

    # 2. Si el pago se procesó en esta visita, ejecuta las acciones externas (email, calendario).
    if pago_procesado_ahora:
        google_calendar_link_email = create_google_calendar_link(reserva)
        
        # Enviar correo de confirmación EN BACKGROUND
        import threading
        
        def send_confirmation_email():
            subject_confirm = '✅ Confirmación: Tu cupo en la Preventa TerraTokenX está asegurado'
            context_confirm = {
                'reserva': reserva,
                'google_calendar_link': google_calendar_link_email,
            }
            html_message_confirm = render_to_string('booking/email/reservation_confirmation.html', context_confirm)
            try:
                send_mail(
                    subject_confirm, '',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[reserva.correo],
                    fail_silently=False,
                    html_message=html_message_confirm
                )
                print(f"[EMAIL] Correo confirmación enviado a {reserva.correo}")
            except Exception as e:
                logger.error(f"Error enviando correo de confirmación: {e}")
                print(f"[EMAIL ERROR] {e}")
        
        email_thread = threading.Thread(target=send_confirmation_email)
        email_thread.start()
        
        # Agregar evento al calendario del negocio
        add_event_to_spa_calendar(reserva)

    # Crear el enlace de Google Calendar para mostrarlo en la página de éxito
    google_calendar_link = create_google_calendar_link(reserva)

    context = {
        'reserva': reserva,
        'payment_status': payment_status,
        'google_calendar_link': google_calendar_link,
    }
    return render(request, 'booking/reservation_success.html', context)


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

def crear_orden_cryptomarket(request, reserva):
    """
    Placeholder para la integración con CryptoMarket.
    Por ahora retorna una respuesta simulada o redirige a una página de 'Pendiente'.
    """
    return redirect('payment_crypto_view', reserva_id=reserva.id)


def simulate_crypto_payment(request, reserva_id):
    """
    Vista de simulación para desarrollo - marca la reserva como pagada.
    SOLO PARA TESTING LOCAL - NO USAR EN PRODUCCIÓN.
    """
    from django.shortcuts import get_object_or_404, resolve_url
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    
    from django.http import Http404
    
    # PROTECCIÓN: Solo permitir en modo DEBUG
    if not settings.DEBUG:
        raise Http404("Página no encontrada en Producción")

    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    # Marcar como pagado (IMPORTANTE: debe ser pagado=True, no estado)
    reserva.pagado = True
    reserva.save()
    
    # Enviar correo de confirmación EN BACKGROUND
    import threading
    
    def send_simulation_email():
        try:
            context = {'reserva': reserva, 'google_calendar_link': '#'}
            html_message = render_to_string('booking/email/reservation_confirmation.html', context)
            send_mail(
                subject='🎉 ¡Tu inversión en TerraTokenX ha sido confirmada!',
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[reserva.correo],
                fail_silently=False,
                html_message=html_message,
            )
            print(f"[SIMULATION] Email enviado exitosamente a {reserva.correo}")
        except Exception as e:
            print(f"[SIMULATION] ERROR enviando email: {e}")
    
    email_thread = threading.Thread(target=send_simulation_email)
    email_thread.start()
    
    # Redirigir con status approved (NO ESPERA al email)
    url = resolve_url('reservation_success', reserva_id=reserva.id)
    return redirect(f'{url}?status=approved')

def preview_email(request):
    """
    Vista temporal para previsualizar el correo de confirmación.
    """
    class DummyReserva:
        nombre = "Juan Pérez"
        total = 1000000
        numero_reserva = "ORD-2024-001"
        def get_metodo_pago_display(self):
            return "Mercado Pago"
    
    reserva = DummyReserva()
    
    return render(request, 'booking/email/reservation_confirmation.html', {'reserva': reserva})


from django.http import JsonResponse
import json

def validate_coupon(request):
    """
    Validates a coupon code via AJAX.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip()
            
            try:
                coupon = Coupon.objects.get(code=code)
                if coupon.is_valid():
                    return JsonResponse({
                        'valid': True,
                        'discount_percentage': coupon.discount_percentage,
                        'message': f'¡Cupón válido! {coupon.discount_percentage}% de descuento aplicado.'
                    })
                else:
                    return JsonResponse({
                        'valid': False,
                        'message': 'El cupón ha expirado o no está activo.'
                    })
            except Coupon.DoesNotExist:
                return JsonResponse({
                    'valid': False,
                    'message': 'Código de cupón no encontrado.'
                })
        except Exception as e:
            return JsonResponse({'valid': False, 'message': 'Error procesando la solicitud.'}, status=400)
    
    return JsonResponse({'valid': False, 'message': 'Método no permitido.'}, status=405)


# --- DIY Crypto Payment Views ---
from .cryptomkt_api import CryptoMarketAPI
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

def payment_crypto_view(request, reserva_id):
    """Muestra la página de selección de moneda y pago."""
    reserva = get_object_or_404(Reserva, id=reserva_id)
    return render(request, 'booking/payment_crypto.html', {'reserva': reserva})

def api_get_crypto_details(request):
    """
    AJAX: Calcula el monto en crypto y obtiene la dirección de depósito.
    CORRECCIÓN: Conversión basada en USD real usando API pública (Binance).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
        
    try:
        data = json.loads(request.body)
        reserva_id = data.get('reserva_id')
        currency = data.get('currency')
        
        if not reserva_id or not currency:
            return JsonResponse({'success': False, 'error': 'Faltan parámetros'})
            
        reserva = get_object_or_404(Reserva, id=reserva_id)
        
        # 1. Obtener precio actual en USD (Estrategia Binance -> Fallback)
        from .cryptomkt_api import get_crypto_price_in_usd
        price_usd = get_crypto_price_in_usd(currency)
        
        if not price_usd or price_usd <= 0:
            return JsonResponse({
                'success': False, 
                'error': f'No se pudo obtener el precio de mercado para {currency}. Intenta más tarde.'
            })
            
        # 2. Calcular monto (Reserva.total está en USD)
        total_usd = float(reserva.total)
        crypto_amount = total_usd / price_usd
        crypto_amount = round(crypto_amount, 8)
        
        logger.info(f"Conversión: ${total_usd} USD / ${price_usd} ({currency}) = {crypto_amount}")
        
        # 3. Obtener dirección (Usamos la clase API de CryptoMarket para la wallet)
        from .cryptomkt_api import get_wallet_address
        address = get_wallet_address(currency)
        
        if not address:
             # Fallback secundario: direcciones estáticas en settings si la API de wallet falla
             static_addresses = {
                 'ETH': getattr(settings, 'CRYPTOMKT_WALLET_ETH', ''),
                 'BTC': getattr(settings, 'CRYPTOMKT_WALLET_BTC', ''),
                 'USDT': getattr(settings, 'CRYPTOMKT_WALLET_USDT', ''),
                 'USDC': getattr(settings, 'CRYPTOMKT_WALLET_USDC', ''),
             }
             address = static_addresses.get(currency)
             
        if not address:
             return JsonResponse({'success': False, 'error': 'No se pudo generar dirección de depósito. Contacta soporte.'})
             
        # 4. Guardar datos en la reserva
        reserva.crypto_amount = crypto_amount
        reserva.crypto_currency = currency
        reserva.crypto_address = address
        reserva.payment_window_start = timezone.now()
        reserva.save()
        
        return JsonResponse({
            'success': True,
            'amount': f"{crypto_amount:.8f}",
            'currency': currency,
            'address': address,
            'exchange_rate': price_usd
        })
        
    except Exception as e:
        logger.error(f"Error en api_get_crypto_details: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

def api_check_payment_status(request):
    """
    AJAX: Polling para verificar si el pago llegó.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False})
        
    try:
        data = json.loads(request.body)
        reserva_id = data.get('reserva_id')
        reserva = get_object_or_404(Reserva, id=reserva_id)
        
        if reserva.pagado:
             return JsonResponse({'confirmed': True})
             
        if not reserva.crypto_amount or not reserva.crypto_currency:
             return JsonResponse({'confirmed': False})
             
        api = CryptoMarketAPI()
        
        # Verificar en blockchain/exchange
        confirmed = api.check_payment(
            reserva.crypto_currency, 
            reserva.crypto_amount, 
            reserva.payment_window_start
        )
        
        if confirmed:
            reserva.pagado = True
            reserva.metodo_pago = 'CRYPTO'
            reserva.save()
            
            # Enviar correo confirmación
            try:
                # Usar template existente o uno genérico
                context = {'reserva': reserva}
                # Intentar usar el template de confirmación estándar si existe
                msg_html = render_to_string('booking/email/reservation_confirmation.html', context)
                send_mail(
                    subject=f'Pago Confirmado - Reserva #{reserva.numero_reserva}',
                    message='',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[reserva.correo],
                    html_message=msg_html
                )
            except Exception as e:
                print(f"Error enviando email confirmación: {e}")
                
            return JsonResponse({'confirmed': True})
            
        return JsonResponse({'confirmed': False})
        
    except Exception:
        return JsonResponse({'confirmed': False})

def api_manual_confirm_payment(request):
    """
    AJAX: El usuario confirma manualmente que ha enviado el pago.
    Envia correo al administrador y redirige al usuario.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
        
    try:
        data = json.loads(request.body)
        reserva_id = data.get('reserva_id')
        reserva = get_object_or_404(Reserva, id=reserva_id)
        
        # Marcar como "En Revisión" - el admin debe verificar manualmente antes de confirmar
        reserva.estado_pago = Reserva.ESTADO_EN_REVISION
        reserva.metodo_pago = 'CRYPTO_MANUAL'
        # Asegurar que la dirección es la fija para manual
        reserva.crypto_address = '0x1FE826766718D9Aa9fb0AE85277b7046e4aC3134'
        reserva.save()
        
        # Enviar correo de confirmación al CLIENTE
        try:
            context = {'reserva': reserva}
            msg_html = render_to_string('booking/email/reservation_confirmation.html', context)
            send_mail(
                subject=f'Pago Reportado - Reserva #{reserva.numero_reserva}',
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[reserva.correo],
                html_message=msg_html
            )
        except Exception as e:
            logger.error(f"Error enviando email cliente manual: {e}")

        # Enviar alerta al ADMIN (Joan)
        try:
            admin_email = "contacto@terratokenx.com" # O el correo de Joan
            msg_admin = f"""
            El usuario {reserva.nombre} ha reportado un pago manual.
            Reserva: #{reserva.numero_reserva}
            Monto: {reserva.crypto_amount} {reserva.crypto_currency}
            Dirección: {reserva.crypto_address}
            
            POR FAVOR VERIFICA EN CRYPTOMARKET.
            """
            send_mail(
                subject=f'⚠️ VERIFICAR PAGO CRYPTO #{reserva.numero_reserva}',
                message=msg_admin,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
            )
        except Exception as e:
            logger.error(f"Error enviando alerta admin: {e}")
            
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def api_stats(request):
    """
    API pública para obtener estadísticas de tokens vendidos/disponibles.
    Soporta ?project_id=X o ?slug=refugio-patagonia
    Si no se especifica, carga el proyecto por defecto (Refugio Patagonia).
    """
    from django.db.models import Sum
    from .models import Proyecto
    
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
    from .models import Proyecto, Configuracion
    
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
    from .models import Proyecto
    
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
    from .models import Proyecto
    
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

@login_required # Assuming standard Django auth for admin panel
@user_passes_test(lambda u: u.is_superuser)
def admin_projects(request):
    """
    Vista para listar proyectos en el panel de administración.
    """
    from .models import Proyecto
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
    from .forms import ProyectoForm
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
    from .models import Proyecto, ProyectoDocumento
    
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
    from .models import ProyectoDocumento
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
    from .models import Proyecto, ProyectoSeccion
    
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
    from .models import ProyectoSeccion
    
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
    from .models import ProyectoSeccion
    
    seccion = get_object_or_404(ProyectoSeccion, pk=section_id)
    project_id = seccion.proyecto.id
    nombre = seccion.nombre
    seccion.delete()
    messages.success(request, f'Sección "{nombre}" eliminada.')
    
    return redirect('project_edit', project_id=project_id)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_project_delete(request, project_id):
    from .models import Proyecto
    
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
from .api_views import firmavirtual_webhook, firmavirtual_status

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
    from .models import UserProfile
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
    from .models import UserProfile
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
    from .models import Reserva

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
    from .models import UserProfile
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
    from .models import UserProfile
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
    from .models import UserProfile
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
    from .models import UserProfile
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
    from .models import UserProfile
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

@login_required(login_url='investor_login')
def fractionalizer_onboarding(request):
    """
    Vista para postulación de Fraccionadores (KYB).
    """
    from .models import UserProfile
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
    from .models import Proyecto
    
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
    
    from .models import UserProfile
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
    from .models import Proyecto, ProyectoImagen
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
    from .models import Proyecto
    from .forms import FractionalizerProjectForm

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



@login_required
def verification(request):
    """
    Vista para subir documentos KYC.
    """
    # Defensive check: crear perfil si no existe
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.get_or_create(user=request.user)
    
    profile = request.user.profile
    
    if request.method == 'POST':
        try:
            updated = False
            # Procesar archivos
            if 'documento_frontal' in request.FILES:
                profile.documento_identidad_frontal = request.FILES['documento_frontal']
                updated = True
            if 'documento_reverso' in request.FILES:
                profile.documento_identidad_reverso = request.FILES['documento_reverso']
                updated = True
            if 'selfie' in request.FILES:
                profile.selfie_verificacion = request.FILES['selfie']
                updated = True
            
            if updated:
                # Cambiar estado a REVISION
                profile.kyc_status = 'REVISION' 
                profile.fecha_kyc = timezone.now()
                profile.save()
                messages.success(request, "Documentos recibidos correctamente. Tu cuenta está ahora EN REVISIÓN.")
            else:
                messages.warning(request, "No se adjuntaron documentos nuevos.")
            
            return redirect('verification')
            
        except Exception as e:
            messages.error(request, f"Error al subir documentos: {e}")
    
    context = {
        'user_profile': profile,
        'kyc_tier_label': f"Nivel {profile.kyc_tier}",
        'remaining_usd': "{:,.0f}".format(profile.remaining_limit),
    }
    return render(request, 'booking/verification.html', context)
