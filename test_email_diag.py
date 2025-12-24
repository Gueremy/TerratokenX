import os
import sys
import django

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment BEFORE importing models/settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email():
    print("--- INICIANDO DIAGNÓSTICO DE EMAIL ---")
    print(f"Backend: {settings.EMAIL_BACKEND}")
    print(f"Host: {settings.EMAIL_HOST}")
    print(f"Port: {settings.EMAIL_PORT}")
    print(f"TLS: {settings.EMAIL_USE_TLS}")
    print(f"User: {settings.EMAIL_HOST_USER}")
    print(f"From Email: {settings.DEFAULT_FROM_EMAIL}")
    
    try:
        print("\nIntentando enviar correo de prueba...")
        send_mail(
            'Prueba Diagnóstico TerraTokenX',
            'Si recibes esto, el correo funciona correctamente desde Render.',
            settings.DEFAULT_FROM_EMAIL,
            ['gueremybtos@gmail.com'], # Enviando a tu propio correo verificado
            fail_silently=False,
        )
        print("✅ CORREO ENVIADO EXITOSAMENTE (Según Django)")
    except Exception as e:
        print("❌ ERROR FATAL AL ENVIAR:")
        print(f"{e}")

if __name__ == '__main__':
    test_email()
