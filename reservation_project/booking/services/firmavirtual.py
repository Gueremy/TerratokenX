
import requests
import json
import base64
import io
from django.conf import settings
from django.core.cache import cache


class FirmaVirtualService:
    """
    Servicio para integración con FirmaVirtual (Trámit Express).
    
    Especificación API:
    - Endpoint Login: /user-data-login (POST)
    - Endpoint Contrato: /tramit-express (POST)
    - Token expira cada 48-72 horas
    - Lógica de retry automático en caso de 401
    """
    
    def __init__(self):
        self.base_url = settings.FIRMAVIRTUAL_BASE_URL
        self.username = settings.FIRMAVIRTUAL_USER
        self.password = settings.FIRMAVIRTUAL_PASS
        self.token_key = "firmavirtual_access_token"

    def _get_auth_token(self):
        """
        Obtiene el token de autenticación. Intenta leerlo de caché (Redis/LocMem),
        si no existe o expiró, se loguea nuevamente.
        """
        token = cache.get(self.token_key)
        if token:
            return token

        # Si no hay token, loguearse usando el endpoint que funciona
        url = f"{self.base_url}/logindata"
        payload = {
            "login": self.username,
            "password": self.password
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Manejar diferentes formatos de respuesta
                    if isinstance(data.get("message"), dict):
                        token = data.get("message", {}).get("Authorization")
                    else:
                        token = data.get("Authorization")
                    
                    if token:
                        # Token válido por 48 horas (guardamos 24h para margen de seguridad)
                        cache.set(self.token_key, token, timeout=86400)
                        return token
                except ValueError:
                    print(f"Error: Respuesta no es JSON válido: {response.text[:200]}")
                    return None
            print(f"Error Login FirmaVirtual ({response.status_code}): {response.text[:200]}")
            return None
        except Exception as e:
            print(f"Excepción Login FirmaVirtual: {str(e)}")
            return None

    def _invalidate_token(self):
        """Invalida el token en caché para forzar re-autenticación."""
        cache.delete(self.token_key)

    def _generate_pdf_base64(self, html_content):
        """
        Genera un PDF a partir de contenido HTML y lo convierte a Base64.
        Usa xhtml2pdf para evitar dependencias de GTK/Pango.
        """
        from xhtml2pdf import pisa
        
        # Crear buffer en memoria para el PDF
        pdf_buffer = io.BytesIO()
        
        # Convertir HTML a PDF
        pisa_status = pisa.CreatePDF(
            src=html_content,
            dest=pdf_buffer,
            encoding='utf-8'
        )
        
        if pisa_status.err:
            print(f"Error generando PDF con xhtml2pdf: {pisa_status.err}")
            return None
            
        # Obtener bytes del PDF
        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        # Codificar a Base64
        return base64.b64encode(pdf_bytes).decode('utf-8')

    def create_contract_request(self, reserva, retry_on_401=True):
        """
        Crea una solicitud de firma (Trámite Express - contractId 49) para la reserva dada.
        Genera un PDF profesional con los datos de la compra y lo envía a la API.
        
        Args:
            reserva: Instancia del modelo Reserva
            retry_on_401: Si True, reintenta automáticamente al recibir 401
            
        Returns:
            dict: Respuesta de la API o diccionario con 'error'
        """
        token = self._get_auth_token()
        if not token:
            return {"error": "No se pudo autenticar con FirmaVirtual"}

        from django.template.loader import render_to_string
        from django.utils import timezone

        # 1. Generar contenido del Documento usando Template HTML Profesional
        context = {
            'fecha_actual': timezone.now().strftime('%d de %B de %Y'),
            'nombre': reserva.nombre,
            'rut': reserva.rut,
            'email': reserva.correo,
            'telefono': reserva.telefono,
            'direccion': reserva.direccion,
            'amount': reserva.cantidad_tokens,
            'project_name': reserva.proyecto.nombre if reserva.proyecto else 'Proyecto General',
            'total': f"{reserva.total:,.0f}",
            # Datos Empresa
            'es_empresa': reserva.es_empresa,
            'razon_social': reserva.razon_social,
            'rut_empresa': reserva.rut_empresa,
            'cargo_representante': reserva.cargo_representante,
        }
        
        try:
            html_content = render_to_string('booking/contract_template.html', context)
        except Exception as e:
            print(f"Error renderizando template contrato: {e}")
            return {"error": f"Error generando contrato: {e}"}

        # 2. Generar PDF y convertir a Base64
        document_b64 = self._generate_pdf_base64(html_content)
        if not document_b64:
            return {"error": "Error generando PDF del contrato"}

        # 3. Definir Nombre del Contrato 
        # FIRMAVIRTUAL_TEST_MODE=True → Nombre con "Prueba" (NO se factura)
        # FIRMAVIRTUAL_TEST_MODE=False → Nombre normal (SÍ se factura)
        # Default=True para evitar cobros accidentales en producción
        test_mode = getattr(settings, 'FIRMAVIRTUAL_TEST_MODE', True)
        
        if test_mode:
            contract_name = f"Prueba Venta {reserva.id} - NO COBRAR"
        else:
            contract_name = f"Compra Token {reserva.numero_reserva}"

        # 4. Sanitización de Datos
        # RUT: Eliminar puntos, mantener guión (12.345.678-9 -> 12345678-9)
        rut_clean = reserva.rut.replace(".", "") if reserva.rut else ""
        
        # Teléfono: Asegurar formato internacional
        phone = reserva.telefono or ""
        if phone and not phone.startswith("+"):
            phone = f"+56{phone.lstrip('0')}"

        # 5. Payload según especificación API oficial v1.22
        # Endpoint correcto: /api/v1/contract/create-contract-express
        url = f"{self.base_url}/api/v1/contract/create-contract-express"
        
        # Obtener callback URL de settings
        callback_url = getattr(settings, 'TRAMIT_CALLBACK_URL', 
                               'https://api.midominio.com/webhooks/tramit-status/')
        
        # PAYLOAD según especificación API oficial v1.22
        # El convenio de facturación se detecta automáticamente por la cuenta.
        # IMPORTANTE: En DEBUG, sContractName debe incluir "Prueba" para no ser facturado
        
        payload = {
            # === CAMPOS REQUERIDOS (según documentación) ===
            "sOwnerType": "NATURAL",  # Tipo de creador: 'NATURAL' o 'LEGAL' (REQUERIDO)
            "iContractTypeFeeID": 49,  # ID del tipo de contrato (REQUERIDO)
            "iSignedCount": 1,  # Cantidad de firmantes (REQUERIDO)
            "signers": [
                {
                    "full_name": reserva.nombre,  # REQUERIDO
                    "email": reserva.correo,  # REQUERIDO
                    "rutId": rut_clean,  # REQUERIDO - SIN puntos, CON guión
                    "phone": phone,  # REQUERIDO - Con código país (569...)
                    "rol": 0,  # REQUERIDO - 0=firmante, 3=pagador
                    "order": 1,  # REQUERIDO - Orden de firma
                    "type": "NATURAL",  # REQUERIDO - Siempre 'NATURAL' para firmantes
                    "portion": "100",  # REQUERIDO - Porcentaje de participación
                    "payment": "0.00",  # Campo presente en ejemplos
                }
            ],
            "document": {
                "content_file": document_b64  # REQUERIDO - PDF en Base64
            },
            
            # === CAMPOS OPCIONALES ===
            "sContractName": contract_name,  # "Prueba..." en DEBUG para evitar facturación
            "callback": callback_url,  # URL para notificaciones de estado
        }
        
        headers = {
            "Authorization": f"Bearer {token}" if not token.startswith("Bearer") else token,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            print(f"Respuesta FirmaVirtual ({response.status_code}): {response.text[:500]}")
            
            # Manejo de 401 Unauthorized - Retry automático
            if response.status_code == 401 and retry_on_401:
                print("Token expirado, renovando y reintentando...")
                self._invalidate_token()
                return self.create_contract_request(reserva, retry_on_401=False)
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                return {"error": f"Error API ({response.status_code}): {response.text}"}
                
        except Exception as e:
            return {"error": str(e)}
