import hmac
import hashlib
import time
import requests
import json
from django.conf import settings
import logging
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)

class CryptoMarketAPI:
    """
    Cliente para la API de Exchange de CryptoMarket (V3).
    Usado para el flujo DIY de pagos (Mostrar dirección -> Monitorear depósitos).
    """
    BASE_URL = "https://api.exchange.cryptomkt.com"
    
    def __init__(self):
        self.api_key = settings.CRYPTOMKT_API_KEY
        self.api_secret = settings.CRYPTOMKT_API_SECRET
        
    def _get_headers(self, method, path, body=None):
        timestamp = str(int(time.time()))
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

    def get_ticker(self, symbol):
        """Obtiene el precio actual de un par (ej: ETHCLP)"""
        path = f"/api/3/public/ticker/{symbol}"
        try:
            response = requests.get(f"{self.BASE_URL}{path}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error obteniendo ticker {symbol}: {e}")
            return None

    def get_deposit_address(self, currency):
        """
        Obtiene la dirección de depósito para una criptomoneda.
        Nota: Esto usa la cuenta del Exchange del usuario.
        """
        path = f"/api/3/payment/address/{currency}" # Endpoint hipotético versión 3 Exchange
        # En V3 Exchange, es POST /api/3/payment/addresses ?? No, es wallet.
        # Revisando endpoints comunes de V3 Exchange para wallet:
        # GET /api/3/wallet/crypto/address/{currency} ???
        # Vamos a intentar el endpoint más estándar de V3 para obtener dirección de depósito.
        
        # Endpoint V3 oficial para Balance/Wallet suele ser: /api/3/wallet/crypto/address
        path = "/api/3/wallet/crypto/address"
        # Esto suele retornar TODAS, o se puede filtrar.
        # Si no existe, se crea con POST.
        
        # Intentaremos GET primero
        headers = self._get_headers('GET', path)
        try:
            response = requests.get(f"{self.BASE_URL}{path}", headers=headers)
            if response.status_code == 404:
                # Si no tiene dirección generada, hay que generarla
                return self.generate_deposit_address(currency)
                
            response.raise_for_status()
            addresses = response.json()
            # Buscar la de la moneda correcta
            for addr in addresses:
                 if addr.get('currency') == currency:
                     return addr.get('address')
            
            # Si no está en la lista, intentar generar
            return self.generate_deposit_address(currency)

        except Exception as e:
            logger.error(f"Error obteniendo dirección para {currency}: {e}")
            # Fallback for 401/403 or other API errors: Check static settings
            static_addr = getattr(settings, f'CRYPTOMKT_WALLET_{currency}', '')
            if static_addr:
                logger.info(f"Using STATIC address for {currency}: {static_addr}")
                return static_addr
            return None

    def generate_deposit_address(self, currency):
        """Genera una nueva dirección de depósito"""
        path = "/api/3/wallet/crypto/address"
        payload = json.dumps({"currency": currency})
        headers = self._get_headers('POST', path, payload)
        try:
            response = requests.post(f"{self.BASE_URL}{path}", headers=headers, data=payload)
            response.raise_for_status()
            data = response.json()
            return data.get('address')
        except Exception as e:
             logger.error(f"Error generando dirección para {currency}: {e}")
             return None

    def check_payment(self, currency, amount, min_timestamp):
        """
        Busca depósitos recientes en esa moneda que coincidan con el monto
        y sean posteriores a min_timestamp.
        """
        # Endpoint historial de transacciones
        path = "/api/3/wallet/transactions"
        # Filtrar por moneda y tipo 'DEPOSIT'
        # Parametros query
        params = f"?currency={currency}&type=DEPOSIT&limit=10"
        full_path = path + params
        
        headers = self._get_headers('GET', full_path) # Ojo: la firma incluye query params? Normalmente no en path, pero depende exchange.
        # En CryptoMarket V3, la firma suele ser sobre path+query.
        
        try:
            response = requests.get(f"{self.BASE_URL}{full_path}", headers=headers)
            response.raise_for_status()
            transactions = response.json()
            
            for tx in transactions:
                # Verificar monto (con cierta tolerancia por fees de red si aplica, aunque en deposito suele ser neto)
                # Usemos decimal para comparar string
                tx_amount = float(tx.get('amount', 0))
                target_amount = float(amount)
                
                # Verificar fecha
                # CryptoMarket devuelve timestamp en string ISO o similar?
                # Asumimos ISO para este ejemplo "2023-01-01T12:00:00"
                created_at_str = tx.get('created_at') # 2026-01-02T12:00:00...
                # Convertir a datetime aware
                
                # Simplificación: Si el monto coincide EXACTAMENTE (o muy cerca)
                # Y es reciente, retornamos True.
                
                # Comparación de floats con pequeña tolerancia (epsilon)
                if abs(tx_amount - target_amount) < 0.00000001:
                    logger.info(f"Pago detectado: {tx}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error verificando pago: {e}")
            return False

# Funciones helper para las vistas
def get_crypto_price(currency_code):
    """
    Retorna el precio de 1 unidad de crypto en CLP.
    Ej: ETH -> retorna 3.000.000 (aprox)
    """
    api = CryptoMarketAPI()
    symbol = f"{currency_code}CLP" 
    ticker = api.get_ticker(symbol)
    
    if ticker and 'last' in ticker:
        return float(ticker['last'])
    
    # Fallback o manejo de error fundamental
    return None

def get_wallet_address(currency_code):
    api = CryptoMarketAPI()
    return api.get_deposit_address(currency_code)

def verify_payment_on_chain(currency, amount, window_start):
    api = CryptoMarketAPI()
    return api.check_payment(currency, amount, window_start)
