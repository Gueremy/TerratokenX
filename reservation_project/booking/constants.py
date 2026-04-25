"""
Constantes centralizadas del proyecto TerraTokenX.

Para estados de modelos, usar siempre las constantes de clase:
  - Reserva.ESTADO_CONFIRMADO, Reserva.ESTADO_PENDIENTE, etc.
  - UserProfile.KYC_APROBADO, UserProfile.TIER_0_BASIC, etc.

Este archivo contiene constantes adicionales que NO viven en modelos.
"""

# ─── Métodos de pago (espejo de Reserva.METODO_PAGO_CHOICES) ──────────────────
class MetodoPago:
    MERCADOPAGO = 'MP'
    CRYPTOMARKET = 'CRYPTO'
    CRYPTO_MANUAL = 'CRYPTO_MANUAL'

    ALL = [MERCADOPAGO, CRYPTOMARKET, CRYPTO_MANUAL]


# ─── Estados de pago (espejo de Reserva.ESTADO_PAGO_CHOICES) ─────────────────
class EstadoPago:
    PENDIENTE = 'PENDIENTE'
    EN_REVISION = 'EN_REVISION'
    CONFIRMADO = 'CONFIRMADO'

    ACTIVOS = [PENDIENTE, EN_REVISION, CONFIRMADO]


# ─── Límites de inversión por tier KYC ───────────────────────────────────────
class KYCLimites:
    TIER_0_LIMITE_USD = 500
    TIER_1_LIMITE_USD = 10_000
    TIER_2_LIMITE_USD = None   # ilimitado


# ─── Ventanas de pago crypto (en minutos) ────────────────────────────────────
CRYPTO_PAYMENT_WINDOW_MINUTES = 60


# ─── Número máximo de tokens por compra por defecto ──────────────────────────
MAX_TOKENS_POR_COMPRA = 100


# ─── Claves de sesión ─────────────────────────────────────────────────────────
SESSION_RESERVA_KEY = 'ultima_reserva_id'
SESSION_PENDING_RESERVA = 'pending_reserva_numero'
