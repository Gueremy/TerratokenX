
import os
import django
from decimal import Decimal

# Configurar entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservation_project.settings')
django.setup()

from django.contrib.auth.models import User
from booking.models import UserProfile, CreditTransaction
from booking.services.credits import (
    comprar_creditos, 
    crear_bono_locked_invest, 
    usar_creditos, 
    get_creditos_breakdown,
    get_creditos_disponibles
)
from datetime import timedelta
from django.utils import timezone

def run_tests():
    print("==============================================")
    print("🧪 INICIANDO TEST DE CRÉDITOS PREMIUM (v2.0) 🧪")
    print("==============================================\n")
    
    # 0. Setup Tier (Asegurar que existe BRONZE)
    from booking.models import TierConfig
    if not TierConfig.objects.filter(nombre='BRONZE').exists():
        TierConfig.objects.create(
            nombre='BRONZE', 
            precio_por_1000_creditos=1000, 
            cap_creditos=50000,
            descuento_fees=0,
            kyc_requerido='V0',
            autoservicio=True
        )
        print("🔧 Tier BRONZE creado automágicamente.")

    # 1. Setup User (Limpieza previa)
    username = "test_premium_credits"
    try:
        if User.objects.filter(username=username).exists():
            User.objects.get(username=username).delete()
            print(f"🧹 Usuario previo eliminado.")
    except:
        pass
    
    user = User.objects.create_user(username=username, email="test_credits@example.com", password="password123")
    print(f"✅ Usuario de prueba creado: {user.username}")
    
    # --------------------------------------------------------------------------------
    # TEST 1: Compra Standard (Saldo Usable)
    # --------------------------------------------------------------------------------
    print("\n[TEST 1] Compra Standard (1 bloque = 1000 créditos)")
    # Simulamos compra de 1000 créditos Bronze
    comprar_creditos(user, 'BRONZE', cantidad_bloques=1)
    
    bd = get_creditos_breakdown(user)
    print(f"   📊 Breakdown Actual: {bd}")
    
    assert bd['total'] == Decimal('1000.00'), "❌ FALLO: El total debería ser 1000"
    assert bd['usable'] == Decimal('1000.00'), "❌ FALLO: El saldo usable debería ser 1000"
    assert bd['locked'] == Decimal('0.00'), "❌ FALLO: No debería haber saldo locked"
    print("   ✅ PASADO")

    # --------------------------------------------------------------------------------
    # TEST 2: Asignar Bono Locked (Saldo Locked)
    # --------------------------------------------------------------------------------
    print("\n[TEST 2] Asignar Bono Locked (500 créditos - Cashback)")
    crear_bono_locked_invest(user, 500, "Cashback Promo")
    
    bd = get_creditos_breakdown(user)
    print(f"   📊 Breakdown Actual: {bd}")
    
    # Total esperado: 1500 (1000 usable + 500 locked)
    assert bd['total'] == Decimal('1500.00'), "❌ FALLO: El total debería ser 1500"
    assert bd['usable'] == Decimal('1000.00'), "❌ FALLO: El saldo usable debería seguir en 1000"
    assert bd['locked'] == Decimal('500.00'), "❌ FALLO: El saldo locked debería ser 500"
    print("   ✅ PASADO")

    # --------------------------------------------------------------------------------
    # TEST 3: Gasto Híbrido (Prioridad Usable -> Locked)
    # --------------------------------------------------------------------------------
    # Gastamos 1200 en INVERSIÓN. 
    # Debería consumir: 1000 de USABLE (lo agota) y 200 de LOCKED.
    print("\n[TEST 3] Gasto Inversión (1200 créditos) - Consumo Híbrido")
    usar_creditos(user, 1200, "Inversión Lote 1", purpose="INVESTMENT")
    
    bd = get_creditos_breakdown(user)
    print(f"   📊 Breakdown Actual: {bd}")
    
    # Esperado: 0 Usable, 300 Locked (500 - 200)
    assert bd['usable'] == Decimal('0.00'), "❌ FALLO: El saldo usable debería haberse agotado"
    assert bd['locked'] == Decimal('300.00'), "❌ FALLO: El saldo locked debería ser 300"
    assert bd['total'] == Decimal('300.00'), "❌ FALLO: El total incorrecto"
    print("   ✅ PASADO")

    # --------------------------------------------------------------------------------
    # TEST 4: Gasto Restringido (Fee vs Locked)
    # --------------------------------------------------------------------------------
    # Intentar gastar 100 en FEE (OTHER). Solo queda saldo Locked.
    # El sistema debería PROHIBIRLO.
    print("\n[TEST 4] Intento de Gasto Restringido (Fee Administrativo)")
    try:
        usar_creditos(user, 100, "Fee admin", purpose="OTHER")
        print("   ❌ FALLÓ: El sistema permitió usar bono locked para un FEE (ERROR)")
        raise Exception("Seguridad de Locked Bonus fallida")
    except ValueError as e:
        print(f"   ✅ PASADO: El sistema bloqueó la operación correctamente.")
        print(f"      Mensaje recibido: '{e}'")

    # --------------------------------------------------------------------------------
    # TEST 5: Expiración de Créditos
    # --------------------------------------------------------------------------------
    print("\n[TEST 5] Inyección de Crédito Expirado")
    # Insertar un crédito "viejo" directamente en BD que venció ayer
    CreditTransaction.objects.create(
        user=user,
        monto=1000,
        tipo='COMPRA',
        descripcion='Credito Viejo Vencido',
        fecha_expiracion=timezone.now().date() - timedelta(days=1)
    )
    
    bd = get_creditos_breakdown(user)
    print(f"   📊 Breakdown Actual: {bd}")
    
    # El saldo total NO debería haber cambiado (debe seguir en 300), porque el nuevo crédito ya nació muerto.
    assert bd['total'] == Decimal('300.00'), f"❌ FALLO: Se sumaron créditos vencidos. Total: {bd['total']}"
    print("   ✅ PASADO")

    print("\n==============================================")
    print("🏆 RESULTADO FINAL: SISTEMA 100% OPERATIVO 🏆")
    print("==============================================")

if __name__ == '__main__':
    run_tests()
