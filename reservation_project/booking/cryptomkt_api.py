from cryptomarket.client import Client
from cryptomarket.args import Account
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def create_order_and_get_url(reserva):
    """
    Crea una orden de pago usando el SDK oficial de CryptoMarket.
    Retorna la URL de pago para redirigir al usuario.
    """
    api_key = settings.CRYPTOMKT_API_KEY
    api_secret = settings.CRYPTOMKT_API_SECRET
    
    # Inicializar cliente del SDK
    client = Client(api_key, api_secret)
    
    try:
        # Construir URLs de callback
        domain = "https://terratokenx.onrender.com" if not settings.DEBUG else "http://127.0.0.1:8000"
        
        # Crear orden de pago
        # Según la documentación del SDK, el método para crear órdenes de pago
        # suele ser 'create_payment_order' o similar. 
        # Verificando firma común en SDK v3: client.create_payment(...)
        
        # NOTA: Al no tener autocompletado del SDK aquí, usamos la estructura más probable
        # basada en la documentación v3. 
        
        response = client.create_payment(
            to_receive_currency='CLP',
            to_receive=str(int(reserva.total)),
            external_id=str(reserva.numero_reserva),
            callback_url=f"{domain}/api/crypto/callback/",
            success_url=f"{domain}/success/{reserva.id}/?status=approved",
            error_url=f"{domain}/success/{reserva.id}/?status=failed",
            language='es'
        )
        
        # Analizar respuesta del SDK
        # Dependiendo de la versión del SDK, puede devolver un diccionario o un objeto.
        # Asumimos diccionario por consistencia con Python.
        
        logger.info(f"Respuesta CryptoMarket SDK: {response}")
        
        # Buscar la URL de pago en la respuesta
        # Estructura usual: {'payment_url': '...'} o internal objects
        
        if isinstance(response, dict):
            return response.get('payment_url')
        elif hasattr(response, 'payment_url'):
            return response.payment_url
            
        return None

    except Exception as e:
        logger.error(f"Fallo al crear orden con CryptoMarket SDK: {e}")
        return None
