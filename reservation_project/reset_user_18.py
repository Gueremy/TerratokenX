
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from django.contrib.auth.models import User

try:
    # Buscar usuario específico por ID 18
    user = User.objects.get(pk=18)
    profile = user.profile
    
    print(f"--- ANTES ---")
    print(f"Usuario: {user.username} (ID: {user.id})")
    print(f"Email: {user.email}")
    print(f"Estado KYC actual: '{profile.kyc_status}'")
    print(f"Nivel KYC actual: {profile.kyc_tier}")
    
    # FORZAR RESET
    profile.kyc_status = 'PENDIENTE'
    profile.kyc_tier = 0
    profile.save()
    
    print(f"\n--- DESPUÉS ---")
    print(f"Estado KYC: '{profile.kyc_status}'")
    print(f"Nivel KYC: {profile.kyc_tier}")
    print("✅ Usuario reseteado correctamente. Ahora debería poder ver el formulario de verificación.")

except User.DoesNotExist:
    print("❌ No se encontró el usuario con ID 18.")
except Exception as e:
    print(f"❌ Error: {e}")
