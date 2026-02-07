
import os
import django
import sys

# Configurar el entorno de Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from booking.cryptomkt_api import get_crypto_price_in_usd

def test_conversion():
    currencies = ['BTC', 'ETH', 'USDT']
    amount_usd = 100.0
    
    print("--- Probando Conversión de Precios (Binance/Fallback) ---")
    for crypto in currencies:
        price = get_crypto_price_in_usd(crypto)
        if price:
            crypto_amount = amount_usd / price
            print(f"Token: ${amount_usd} USD -> {crypto}: {price} USD/unit")
            print(f"RESULTADO: {crypto_amount:.8f} {crypto}")
        else:
            print(f"ERROR: No se pudo obtener precio para {crypto}")
        print("-" * 30)

if __name__ == "__main__":
    test_conversion()
