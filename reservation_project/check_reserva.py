
import os
import django
import sys

# Configurar el entorno de Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from booking.models import Reserva

def check_last_reserva():
    reserva = Reserva.objects.all().order_by('-id').first()
    if reserva:
        print(f"Reserva ID: {reserva.id}")
        print(f"Número: {reserva.numero_reserva}")
        print(f"Proyecto: {reserva.proyecto}")
        print(f"Cantidad Tokens: {reserva.cantidad_tokens}")
        if reserva.proyecto:
            print(f"Precio Token (Proyecto): {reserva.proyecto.precio_token}")
        print(f"Total: {reserva.total}")
        print(f"Método Pago: {reserva.metodo_pago}")
        print(f"Crypto Amount: {reserva.crypto_amount}")
        print(f"Crypto Currency: {reserva.crypto_currency}")
    else:
        print("No hay reservas.")

if __name__ == "__main__":
    check_last_reserva()
