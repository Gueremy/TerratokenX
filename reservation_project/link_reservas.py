import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from django.contrib.auth.models import User
from booking.models import Reserva

def link_users():
    print("Linking reservations to users by email...")
    reservas = Reserva.objects.filter(user__isnull=True)
    count = 0
    for r in reservas:
        try:
            user = User.objects.get(email=r.correo)
            r.user = user
            r.save(update_fields=['user'])
            count += 1
        except User.DoesNotExist:
            continue
    print(f"Finished. Linked {count} reservations.")

if __name__ == "__main__":
    link_users()
