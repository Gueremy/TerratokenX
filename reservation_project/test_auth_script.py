import os
import django
from django.test import Client
import random

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from django.contrib.auth.models import User

print("--- Iniciando Pruebas de Autenticación (Backend) ---")

# Configurar Cliente con Host permitido
c = Client(HTTP_HOST='127.0.0.1')

# 1. Prueba Home
print("\n1. Probando Landing Page (/)")
try:
    response = c.get('/')
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Landing Page accesible.")
        if b"Iniciar Sos" in response.content or b"Inicia" in response.content: # Trying simple match
            print("✅ Texto 'Iniciar Sesión' detectado.")
        elif b"Iniciar Sesi" in response.content:
            print("✅ Texto 'Iniciar Sesión' detectado (utf8).")
        else:
            print("⚠️ Advertencia: No se encontró 'Iniciar Sesión'.")
    else:
        print("❌ Error accediendo a /")
except Exception as e:
    print(f"❌ Excepción: {e}")

# 2. Prueba Registro GET
print("\n2. Probando Página de Registro (/auth/register/)")
try:
    response = c.get('/auth/register/')
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Página de Registro accesible.")
    else:
        print("❌ Error accediendo a /auth/register/")
except Exception as e:
    print(f"❌ Excepción: {e}")

# 3. Prueba Registro POST
print("\n3. Probando Creación de Cuenta Automática")
rand_id = random.randint(10000, 99999)
test_email = f"test_auto_{rand_id}@example.com"

data = {
    'first_name': 'Test',
    'last_name': 'Automated',
    'email': test_email,
    'password': 'Password123!',
    'confirm_password': 'Password123!'
}

try:
    response = c.post('/auth/register/', data)
    
    if response.status_code == 302:
        print("✅ Redirección tras registro detectada (Éxito).")
        print(f"   Destino: {response.url}")
        
        # Verificar usuario creado
        if User.objects.filter(email=test_email).exists():
            print(f"✅ Usuario {test_email} creado correctamente en DB.")
            u = User.objects.get(email=test_email)
            if hasattr(u, 'profile'):
                print("✅ UserProfile creado automáticamente.")
            else:
                print("❌ UserProfile NO creado.")
        else:
            print("❌ Usuario NO encontrado en DB tras redirección.")
    else:
        print(f"❌ Fallo en registro. Status: {response.status_code}")
except Exception as e:
    print(f"❌ Excepción en registro: {e}")

# 4. Prueba Acceso Protegido
print("\n4. Probando Protección de Compra (POST sin login)")
c.logout() 
reserva_data = {'cantidad_tokens': 1, 'metodo_pago': 'MP', 'proyecto': 1} 
try:
    response = c.post('/', reserva_data)
    
    if response.status_code == 302:
        print(f"✅ Redirección detectada: {response.url}")
        if 'auth/login' in response.url:
             print("✅ Redirección correcta a Login de Inversores (/auth/login/).")
        elif '/login' in response.url:
             print("⚠️ Redirección a Login Genérico (Posiblemente Admin Login). Revisar si es deseado.")
        else:
             print(f"⚠️ Redirección a URL inesperada: {response.url}")
    else:
        print(f"⚠️ Status inapropiado: {response.status_code}.")
except Exception as e:
    print(f"❌ Excepción en prueba de protección: {e}")

# 5. Prueba Acceso Dashboard sin Login
print("\n5. Probando Protección Dashboard (/mi-cuenta/)")
c.logout()
try:
    response = c.get('/mi-cuenta/')
    if response.status_code == 302:
        print(f"✅ Redirección detectada: {response.url}")
        if 'auth/login' in response.url:
             print("✅ Redirección correcta a Auth Login.")
        else:
             print(f"⚠️ Redirigido a: {response.url} (Probablemente Admin Login).")
    else:
         print(f"❌ Dashboard accesible sin login? Status: {response.status_code}")
except Exception as e:
    print(f"❌ Excepción: {e}")

print("\n--- Fin de Pruebas ---")
