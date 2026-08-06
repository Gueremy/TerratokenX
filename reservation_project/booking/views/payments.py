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
        from ..cryptomkt_api import get_crypto_price_in_usd
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
        from ..cryptomkt_api import get_wallet_address
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
