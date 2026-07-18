from datetime import timedelta
from decimal import Decimal

import factory
from django.contrib.auth.models import User
from django.utils import timezone
from factory.django import DjangoModelFactory

from booking.models import (
    CreditBalance,
    ProjectDrop,
    Proyecto,
    Reserva,
    UserProfile,
)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}@test.cl')
    email = factory.LazyAttribute(lambda o: o.username)
    password = factory.django.Password('testpass123')


class UserProfileFactory(DjangoModelFactory):
    class Meta:
        model = UserProfile
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)
    kyc_tier = 1
    investment_total_usd = Decimal('0.00')


class ProyectoFactory(DjangoModelFactory):
    class Meta:
        model = Proyecto

    nombre = factory.Sequence(lambda n: f'Terreno Patagonia {n}')
    slug = factory.Sequence(lambda n: f'terreno-patagonia-{n}')
    owner = factory.SubFactory(UserFactory)
    owner_type = 'EXTERNAL'
    precio_token = Decimal('100.00')
    tokens_totales = 1000
    activo = True


class DropFactory(DjangoModelFactory):
    class Meta:
        model = ProjectDrop

    proyecto = factory.SubFactory(ProyectoFactory)
    nombre = 'Drop 1'
    numero = 1
    stock_total = 300
    stock_disponible = 300
    precio_override = None
    fecha_inicio = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1))
    fecha_fin = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    activo = True


class ReservaFactory(DjangoModelFactory):
    class Meta:
        model = Reserva

    user = factory.SubFactory(UserFactory)
    nombre = 'Test User'
    correo = factory.LazyAttribute(lambda o: o.user.email if o.user else 'test@test.cl')
    proyecto = factory.SubFactory(ProyectoFactory)
    cantidad_tokens = 5
    estado_pago = 'PENDIENTE'
    metodo_pago = 'MP'


class CreditBalanceFactory(DjangoModelFactory):
    class Meta:
        model = CreditBalance
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)
    balance_usd = Decimal('100.00')
    tier = 1
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=365))
