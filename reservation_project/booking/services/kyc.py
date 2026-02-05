from django.core.exceptions import ValidationError
from booking.models import UserProfile, CreditTransaction

def check_kyc_capability(user, monto_intentado):
    """
    Verifica si el usuario tiene capacidad para realizar una transacción
    según su nivel de KYC y su historial de compras.
    """
    profile = user.profile
    
    # Calcular total histórico de compras (créditos adquiridos)
    total_compras = sum(
        t.monto for t in CreditTransaction.objects.filter(user=user, tipo='COMPRA')
    )
    
    nuevo_total = total_compras + monto_intentado
    
    # Límites por nivel (Hardcodificados según Anexo 1)
    # Límites por nivel (Sincronizados con UI)
    LIMIT_LITE = 1000      # < $1,000
    LIMIT_STANDARD = 10000 # < $10,000 (Nivel 2)
    LIMIT_AUREA = 25000    # < $25,000
    # Diamond es ilimitado
    
    limite_actual = 0
    kyc_level = profile.kyc_level
    
    if kyc_level == UserProfile.KYC_LEVEL_LITE:
        limite_actual = LIMIT_LITE
    elif kyc_level == UserProfile.KYC_LEVEL_STANDARD:
        limite_actual = LIMIT_STANDARD
    elif kyc_level == UserProfile.KYC_LEVEL_AUREA:
        limite_actual = LIMIT_AUREA
    elif kyc_level == UserProfile.KYC_LEVEL_DIAMOND:
        return True # Diamond pasa directo
        
    if nuevo_total >= limite_actual:
        if kyc_level == UserProfile.KYC_LEVEL_LITE:
            raise ValidationError(f"Límite LITE excedido (${limite_actual}). Debes verificar tu identidad (Standard) para continuar.")
        elif kyc_level == UserProfile.KYC_LEVEL_STANDARD:
            raise ValidationError(f"Límite STANDARD excedido (${limite_actual}). Se requiere verificación avanzada (Aurea).")
        elif kyc_level == UserProfile.KYC_LEVEL_AUREA:
            raise ValidationError(f"Límite AUREA excedido (${limite_actual}). Contacta a soporte para nivel DIAMOND.")
            
    return True
