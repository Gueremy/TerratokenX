import os
import django
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from django.core.cache import cache

def clear_token():
    cache.delete('firmavirtual_access_token')
    print('Cache cleared')

if __name__ == '__main__':
    clear_token()
