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


def landing_page(request):
    """
    Renderiza la nueva Landing Page Premium (index.html).
    """
    return render(request, 'booking/landing_premium.html')


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


@login_required
def reservation_form(request):
    print("DEBUG: CARGANDO VISTA reservation_form (v2)")
    from ..models import Proyecto, Reserva, Configuracion, ProjectDrop, UserProfile
    
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
            from ..models import UserProfile
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
from ..cryptomkt_api import CryptoMarketAPI
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt




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
