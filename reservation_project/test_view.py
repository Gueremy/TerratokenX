import os
import django
from django.conf import settings
from django.template import loader, Context
from django.test import RequestFactory

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from booking.views import admin_users
from django.contrib.auth.models import User

# Mock request
factory = RequestFactory()
user = User.objects.filter(is_superuser=True).first()
request = factory.get('/admin-panel/users/')
request.user = user

try:
    response = admin_users(request)
    print(f"Status: {response.status_code}")
    print(f"Content Length: {len(response.content)}")
    print(f"Content Preview: {response.content[:200].decode('utf-8')}")
except Exception as e:
    print(f"Error executing view: {e}")
