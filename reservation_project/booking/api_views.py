from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import json
import requests
import base64
import threading
from .models import Reserva

@csrf_exempt
@require_POST
def firmavirtual_webhook(request):
    """
    Endpoint para recibir notificaciones de FirmaVirtual.
    Cuando un cliente firma, FirmaVirtual nos avisa aquí.
    
    URL: POST /api/webhooks/firmavirtual/
    """
    try:
        data = json.loads(request.body)
        
        # Log para debug
        print(f"Webhook FirmaVirtual recibido: {json.dumps(data, indent=2)}")
        
        # FirmaVirtual envía los datos dentro de "contract" como array
        # Formato: {"contract": [{"sContractID": "...", "sStatus": "..."}], "signers": [...]}
        contract_data = None
        contract_id = None
        status = None
        
        # Intentar extraer del formato de array (formato principal de FirmaVirtual)
        if 'contract' in data and isinstance(data['contract'], list) and len(data['contract']) > 0:
            contract_data = data['contract'][0]
            contract_id = contract_data.get('sContractID')
            status = contract_data.get('sStatus')
            print(f"Extraído de contract[0]: ID={contract_id}, Status={status}")
        
        # Fallback: buscar en el nivel raíz (por si cambian el formato)
        if not contract_id:
            contract_id = (
                data.get('sContractID') or 
                data.get('request_id') or 
                data.get('contractId') or 
                data.get('id')
            )
        
        if not status:
            status = (
                data.get('sStatus') or 
                data.get('status') or 
                data.get('state')
            )
        
        # URL del documento firmado (si viene)
        signed_document_url = (
            (contract_data.get('sSignedDocumentUrl') if contract_data else None) or
            data.get('sSignedDocumentUrl') or 
            data.get('document_url')
        )
        
        if not contract_id:
            print("Webhook sin contract_id, datos recibidos:", data)
            return JsonResponse({"error": "No contract_id provided"}, status=400)
        
        # Extraer nombre del contrato para buscar por ID de reserva si es necesario
        contract_name = contract_data.get('sContractName', '') if contract_data else ''
        
        # Buscar la reserva asociada
        reserva = None
        
        # 1. Primero intentar por firmavirtual_id
        try:
            reserva = Reserva.objects.get(firmavirtual_id=contract_id)
            print(f"Reserva encontrada por firmavirtual_id: {reserva.numero_reserva}")
        except Reserva.DoesNotExist:
            pass
        
        # 2. Si no se encontró, intentar extraer el ID de la reserva del nombre del contrato
        # Formato: "Prueba Venta 39 - NO COBRAR" o "Compra Token XXXXXXXX"
        if not reserva and contract_name:
            import re
            # Buscar número de reserva en el nombre (formato: "Venta XX" donde XX es el ID)
            match = re.search(r'Venta (\d+)', contract_name)
            if match:
                reserva_id = match.group(1)
                try:
                    reserva = Reserva.objects.get(id=reserva_id)
                    # Actualizar el firmavirtual_id para futuras referencias
                    reserva.firmavirtual_id = contract_id
                    reserva.save(update_fields=['firmavirtual_id'])
                    print(f"Reserva encontrada por ID en nombre: {reserva.numero_reserva}, firmavirtual_id actualizado")
                except Reserva.DoesNotExist:
                    pass
            
            # También intentar con número de reserva (formato: "Compra Token XXXXXXXX")
            if not reserva:
                match = re.search(r'Token ([A-Z0-9]+)', contract_name)
                if match:
                    numero_reserva = match.group(1)
                    try:
                        reserva = Reserva.objects.get(numero_reserva=numero_reserva)
                        reserva.firmavirtual_id = contract_id
                        reserva.save(update_fields=['firmavirtual_id'])
                        print(f"Reserva encontrada por numero_reserva: {reserva.numero_reserva}, firmavirtual_id actualizado")
                    except Reserva.DoesNotExist:
                        pass
        
        if not reserva:
            print(f"Reserva no encontrada para FV ID: {contract_id}, nombre: {contract_name}")
            return JsonResponse({"error": "Reserva not found"}, status=404)
        
        # Normalizar status
        status_lower = str(status).lower() if status else ''
        
        # Actualizar estado según lo que nos diga FirmaVirtual
        if status_lower in ['signed', 'firmado', 'completed', 'complete']:
            reserva.firmavirtual_status = 'signed'
            
            # Si viene el documento firmado, descargarlo
            if signed_document_url:
                try:
                    _download_and_save_contract(reserva, signed_document_url)
                except Exception as e:
                    print(f"Error descargando contrato: {e}")
            
            reserva.save()
            print(f"✅ Reserva {reserva.numero_reserva} marcada como FIRMADA")
            
            # Enviar email de confirmación (en hilo separado para no bloquear)
            _send_signature_confirmation_email(reserva)
            
        elif status_lower in ['rejected', 'rechazado', 'cancelled']:
            reserva.firmavirtual_status = 'rejected'
            reserva.save()
            print(f"❌ Reserva {reserva.numero_reserva} marcada como RECHAZADA")
            
        elif status_lower in ['pending', 'pendiente', 'sent']:
            reserva.firmavirtual_status = 'pending'
            reserva.save()
            print(f"⏳ Reserva {reserva.numero_reserva} sigue PENDIENTE")
        
        return JsonResponse({"status": "ok", "message": "Webhook processed"})
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        print(f"Error en webhook FirmaVirtual: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


def _download_and_save_contract(reserva, document_url):
    """
    Descarga el contrato firmado desde FirmaVirtual y lo guarda en la reserva.
    """
    try:
        response = requests.get(document_url, timeout=30)
        response.raise_for_status()
        
        # Guardar el PDF en el campo contrato_firmado
        filename = f"contrato_firmado_{reserva.numero_reserva}.pdf"
        reserva.contrato_firmado.save(filename, ContentFile(response.content), save=True)
        print(f"📄 Contrato firmado guardado: {filename}")
        
    except Exception as e:
        print(f"Error descargando contrato firmado: {e}")
        raise


@csrf_exempt
@require_GET
def firmavirtual_status(request, reserva_id):
    """
    Consultar el estado de firma de una reserva.
    
    URL: GET /api/firmavirtual/status/<reserva_id>/
    """
    try:
        reserva = Reserva.objects.get(id=reserva_id)
        
        return JsonResponse({
            "reserva_id": reserva.id,
            "numero_reserva": reserva.numero_reserva,
            "firmavirtual_id": reserva.firmavirtual_id,
            "status": reserva.firmavirtual_status,
            "has_signed_contract": bool(reserva.contrato_firmado),
            "contract_url": reserva.contrato_firmado.url if reserva.contrato_firmado else None
        })
        
    except Reserva.DoesNotExist:
        return JsonResponse({"error": "Reserva not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _send_signature_confirmation_email(reserva):
    """
    Envía email de confirmación de firma al cliente y notificación al admin.
    Se ejecuta en un hilo separado para no bloquear el webhook.
    """
    def send_emails():
        try:
            context = {'reserva': reserva}
            
            # 1. Email al cliente
            client_subject = f"✅ Contrato Firmado - {reserva.numero_reserva}"
            client_html = render_to_string('booking/emails/contract_signed.html', context)
            
            send_mail(
                subject=client_subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[reserva.correo],
                fail_silently=False,
                html_message=client_html,
            )
            print(f"📧 Email de confirmación enviado a {reserva.correo}")
            
            # 2. Email al admin
            admin_subject = f"📝 Nueva Firma: {reserva.nombre} - {reserva.numero_reserva}"
            admin_html = render_to_string('booking/emails/contract_signed_admin.html', context)
            
            # Obtener email del admin desde settings o usar default
            admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
            
            send_mail(
                subject=admin_subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                fail_silently=False,
                html_message=admin_html,
            )
            print(f"📧 Notificación de admin enviada a {admin_email}")
            
        except Exception as e:
            print(f"❌ Error enviando email de confirmación de firma: {e}")
    
    # Ejecutar en hilo separado
    email_thread = threading.Thread(target=send_emails)
    email_thread.start()
