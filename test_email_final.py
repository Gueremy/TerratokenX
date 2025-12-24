import os
import sys
import django
from django.core.mail import send_mail
from django.conf import settings

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

def test_sendgrid():
    print("--- SendGrid Email Diagnostic ---")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    recipient = "gueremybarrientos058@gmail.com" # Target email from user screenshot
    
    print(f"\nAttempting to send email to: {recipient}")
    try:
        send_mail(
            subject='Prueba Final SendGrid - Admin Project',
            message='Si ves esto, la configuración es correcta y SendGrid funciona.',
            from_email='gueremybtos@gmail.com', # Explicitly using the verified sender
            recipient_list=[recipient],
            fail_silently=False,
        )
        print("\nSUCCESS: Email sent successfully! Check your inbox (and spam).")
    except Exception as e:
        print(f"\nFAILURE: Could not send email.")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sendgrid()
