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
    Cliente manual para la API de Pagos de CryptoMarket (CryptoMarket Pay).
    """
    
    # URL Base sujeta a confirmación con documentación oficial
    # Se ha probado: 
    # - https://api.exchange.cryptomkt.com/api/payment/v1/orders (404)
    # - https://api.exchange.cryptomkt.com/api/3/payment/orders (404)
    BASE_URL = "https://api.exchange.cryptomkt.com"
    
    def __init__(self):
        self.api_key = settings.CRYPTOMKT_API_KEY
        self.api_secret = settings.CRYPTOMKT_API_SECRET
        
    def _get_headers(self, method, path, body=None):
        timestamp = str(int(time.time()))
        
        # Formato estándar de firma CryptoMarket
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
        Crea una orden de pago.
        """
        # Endpoint PROBABLE. Si falla, se verá en los logs.
        path = "/api/payment/v1/orders"
        
        domain = "https://terratokenx.onrender.com" if not settings.DEBUG else "http://127.0.0.1:8000"
        
        payload = {
            "to_receive_currency": "CLP",
            "to_receive": str(int(reserva.total)),
            "external_id": str(reserva.numero_reserva),
            "callback_url": f"{domain}/api/crypto/callback/",
            "success_url": f"{domain}/success/{reserva.id}/?status=approved",
            "error_url": f"{domain}/success/{reserva.id}/?status=failed",
            "language": "es"
        }
        
        body = json.dumps(payload)
        headers = self._get_headers('POST', path, body)
        
        url = f"{self.BASE_URL}{path}"
        logger.info(f"Intentando crear orden en: {url}")
        
        try:
            response = requests.post(url, headers=headers, data=body)
            
            # Loguear respuesta si falla para debugging
            if not response.ok:
                logger.error(f"CryptoMarket Error {response.status_code}: {response.text}")
                
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Excepción conectando con CryptoMarket: {str(e)}")
            raise e

def create_order_and_get_url(reserva):
    """
    Helper function para crear la orden y obtener la URL de pago.
    """
    client = CryptoMarketAPI()
    try:
        data = client.create_payment_order(reserva)
        # Ajustar según la estructura de respuesta real cuando la tengamos
        if 'data' in data and 'payment_url' in data['data']:
             return data['data']['payment_url']
        return None
    except Exception:
        return None
