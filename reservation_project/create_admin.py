import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from django.contrib.auth.models import User

user = User.objects.get(username='admin')
user.set_password('admin123')
user.save()
print("Password for 'admin' reset to 'admin123'")
