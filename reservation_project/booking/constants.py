from django.db import models


class EstadoPago(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    EN_REVISION = 'EN_REVISION', 'En revisión'
    CONFIRMADO = 'CONFIRMADO', 'Confirmado'
    RECHAZADO = 'RECHAZADO', 'Rechazado'
    FALLIDO = 'FALLIDO', 'Fallido'
    REEMBOLSADO = 'REEMBOLSADO', 'Reembolsado'


class MetodoPago(models.TextChoices):
    MP = 'MP', 'MercadoPago'
    CRYPTO = 'CRYPTO', 'Cryptomus'
    KUSHKI = 'KUSHKI', 'Kushki'
    CREDITO = 'CREDITO', 'Créditos RWA'


KYC_LIMITS_USD = {
    1: 1_000,    # Bronze
    2: 5_000,    # Silver
    3: 15_000,   # Gold
    4: 100_000,  # Black VIP
}

TIER_NOMBRES = {
    1: 'Bronze',
    2: 'Silver',
    3: 'Gold',
    4: 'Black VIP',
}

TIER_DESCUENTO_CREDITOS = {
    1: 10,
    2: 20,
    3: 30,
    4: 40,
}
