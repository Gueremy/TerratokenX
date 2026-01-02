import hmac
import hashlib
import time
import requests
import json
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class CryptoMarketAPI:
    """
    Cliente para la API v3 de CryptoMarket.
    Documentación: https://api.exchange.cryptomkt.com/
    """
    
    BASE_URL = "https://api.exchange.cryptomkt.com"
    
    def __init__(self):
        self.api_key = settings.env('CRYPTOMKT_API_KEY')
        self.api_secret = settings.env('CRYPTOMKT_API_SECRET')
        
    def _get_headers(self, method, path, body=None):
        timestamp = str(int(time.time()))
        
        # Formato del mensaje para firmar: timestamp + method + path + body
        message = timestamp + method + path
        if body:
            message += body
            
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'X-MKT-APIKEY': self.api_key,
            'X-MKT-SIGNATURE': signature,
            'X-MKT-TIMESTAMP': timestamp,
            'Content-Type': 'application/json'
        }

    def create_payment_order(self, reserva):
        """
        Crea una orden de pago en CryptoMarket para una reserva.
        """
        path = "/api/3/payment/orders"
        
        # Construir URLs de callback (éxito y falla)
        # Nota: En producción usar HTTPS y el dominio real
        domain = "https://terratokenx.onrender.com" if not settings.DEBUG else "http://127.0.0.1:8000"
        
        # Payload según documentación de Payment API
        payload = {
            "to_receive_currency": "CLP",
            "to_receive": str(int(reserva.total)),  # Monto en CLP
            "external_id": str(reserva.numero_reserva),
            "callback_url": f"{domain}/api/crypto/callback/", # Webhook (opcional si usamos redirect)
            "success_url": f"{domain}/success/{reserva.id}/?status=approved",
            "error_url": f"{domain}/success/{reserva.id}/?status=failed",
            "language": "es"
        }
        
        body = json.dumps(payload)
        headers = self._get_headers('POST', path, body)
        
        try:
            response = requests.post(f"{self.BASE_URL}{path}", headers=headers, data=body)
            response.raise_for_status() # Lanza error si no es 200/201
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP CryptoMarket: {e.response.text}")
            raise e
        except Exception as e:
            logger.error(f"Error conectando con CryptoMarket: {str(e)}")
            raise e

def create_order_and_get_url(reserva):
    """
    Helper function para crear la orden y obtener la URL de pago.
    """
    client = CryptoMarketAPI()
    try:
        data = client.create_payment_order(reserva)
        # La respuesta debería contener la 'payment_url' donde redirigir al usuario
        # Estructura típica: {'data': {'payment_url': '...'}}
        # Ajustaremos según la respuesta real de la API v3
        
        # Si la API retorna directamente el objeto orden dentro de 'data'
        if 'data' in data and 'payment_url' in data['data']:
             return data['data']['payment_url']
             
        # Fallback o log de estructura inesperada
        logger.error(f"Respuesta inesperada de CryptoMarket: {data}")
        return None
        
    except Exception as e:
        logger.error(f"Fallo al crear orden CryptoMarket: {e}")
        return None
