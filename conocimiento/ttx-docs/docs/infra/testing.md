# Testing — TerraTokenX

## Stack de tests

```bash
pip install pytest pytest-django pytest-mock factory-boy faker
```

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = terratokenx.settings.local
python_files = tests/test_*.py
python_classes = Test*
python_functions = test_*
markers =
    blockchain: tests que requieren RPC real (solo en CI con secrets)
    slow: tests lentos (>1 segundo)
```

---

## Factories

```python
# booking/tests/factories.py
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth.models import User
from booking.models import Proyecto, Reserva, ProjectDrop, UserProfile
from booking.models.creditos import CreditBalance
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker('email')
    email    = factory.LazyAttribute(lambda o: o.username)
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')


class UserProfileFactory(DjangoModelFactory):
    class Meta:
        model = UserProfile

    user       = factory.SubFactory(UserFactory)
    kyc_tier   = 1
    investment_total_usd = Decimal('0.00')


class ProyectoFactory(DjangoModelFactory):
    class Meta:
        model = Proyecto

    nombre          = factory.Sequence(lambda n: f'Terreno Patagonia {n}')
    slug            = factory.Sequence(lambda n: f'terreno-patagonia-{n}')
    owner           = factory.SubFactory(UserFactory)
    owner_type      = 'EXTERNAL'
    precio_token    = Decimal('100.00')
    tokens_totales  = 1000
    tokens_vendidos = 0
    activo          = True


class DropFactory(DjangoModelFactory):
    class Meta:
        model = ProjectDrop

    proyecto        = factory.SubFactory(ProyectoFactory)
    nombre          = 'Drop 1'
    numero          = 1
    stock_total     = 300
    stock_disponible = 300
    precio_override = None
    fecha_inicio    = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1))
    fecha_fin       = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    activo          = True


class ReservaFactory(DjangoModelFactory):
    class Meta:
        model = Reserva

    user            = factory.SubFactory(UserFactory)
    proyecto        = factory.SubFactory(ProyectoFactory)
    cantidad_tokens = 5
    total           = Decimal('500.00')
    estado_pago     = 'PENDIENTE'
    metodo_pago     = 'MP'


class CreditBalanceFactory(DjangoModelFactory):
    class Meta:
        model = CreditBalance

    user        = factory.SubFactory(UserFactory)
    balance_usd = Decimal('100.00')
    tier        = 1
    expires_at  = factory.LazyFunction(lambda: timezone.now() + timedelta(days=365))
```

---

## Fixtures de conftest.py

```python
# booking/tests/conftest.py
import pytest
from .factories import (
    UserFactory, UserProfileFactory, ProyectoFactory,
    DropFactory, ReservaFactory, CreditBalanceFactory
)


@pytest.fixture
def user_t1(db):
    user = UserFactory()
    UserProfileFactory(user=user, kyc_tier=1)
    return user


@pytest.fixture
def user_t2(db):
    user = UserFactory()
    UserProfileFactory(user=user, kyc_tier=2)
    return user


@pytest.fixture
def proyecto_activo(db):
    return ProyectoFactory(activo=True)


@pytest.fixture
def drop_activo(db, proyecto_activo):
    return DropFactory(proyecto=proyecto_activo, stock_disponible=50)


@pytest.fixture
def reserva_pendiente(db, user_t1, proyecto_activo):
    return ReservaFactory(user=user_t1, proyecto=proyecto_activo)


@pytest.fixture
def mock_resend(mocker):
    return mocker.patch('booking.integrations.resend._enviar', return_value=True)


@pytest.fixture
def mock_didit(mocker):
    mock = mocker.patch('booking.integrations.didit.requests.post')
    mock.return_value.json.return_value = {
        'session_id': 'sess_test_123',
        'session_url': 'https://verify.didit.me/session/test',
    }
    mock.return_value.raise_for_status = lambda: None
    return mock


@pytest.fixture
def mock_cryptomus(mocker):
    return mocker.patch('booking.integrations.cryptomus.requests.post')
```

---

## Tests críticos — Race Conditions

```python
# booking/tests/test_drops.py
import threading
import pytest
from booking.services import crear_reserva_pendiente
from booking.exceptions import StockInsuficiente


def test_race_condition_stock_no_vende_mas_del_disponible(db, user_t1, drop_activo):
    """
    Dos requests simultáneas intentan comprar el último token.
    Solo una debe tener éxito.
    """
    drop_activo.stock_disponible = 1
    drop_activo.save()

    resultados = []
    errores = []

    def intentar_compra():
        try:
            reserva = crear_reserva_pendiente(
                proyecto_id=drop_activo.proyecto_id,
                user=user_t1,
                cantidad_tokens=1,
                metodo_pago='MP',
            )
            resultados.append(reserva)
        except StockInsuficiente as e:
            errores.append(e)

    # Lanzar dos threads simultáneos
    t1 = threading.Thread(target=intentar_compra)
    t2 = threading.Thread(target=intentar_compra)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Solo una compra debe haber tenido éxito
    assert len(resultados) == 1, f"Esperado 1 éxito, obtenido {len(resultados)}"
    assert len(errores) == 1, f"Esperado 1 error, obtenido {len(errores)}"

    # El stock debe ser 0, no -1
    drop_activo.refresh_from_db()
    assert drop_activo.stock_disponible == 0
```

---

## Tests de webhooks (sin pasarelas reales)

```python
# booking/tests/test_webhooks.py

def test_webhook_mp_firma_invalida(client):
    response = client.post(
        '/api/webhooks/mp/',
        data={'type': 'payment', 'data': {'id': '12345'}},
        content_type='application/json',
        HTTP_X_SIGNATURE='ts=fake,v1=invalida',
    )
    assert response.status_code == 403


def test_webhook_cryptomus_idempotente(client, reserva_confirmada):
    """El mismo webhook procesado dos veces no cambia nada la segunda vez."""
    payload = {
        'uuid': reserva_confirmada.cryptomus_uuid,
        'order_id': str(reserva_confirmada.id),
        'status': 'paid',
        'is_final': True,
        'sign': _generar_firma_test(payload),
    }
    # Primera vez — ya confirmada, debe devolver 200 sin error
    response = client.post('/api/webhooks/cryptomus/', data=payload,
                           content_type='application/json')
    assert response.status_code == 200

    # El estado no debe cambiar (ya era CONFIRMADO)
    reserva_confirmada.refresh_from_db()
    assert reserva_confirmada.estado_pago == 'CONFIRMADO'
```

---

## Correr tests

```bash
# Todos los tests
pytest

# Solo tests de drops
pytest booking/tests/test_drops.py -v

# Tests rápidos (excluir lentos y blockchain)
pytest -m "not slow and not blockchain"

# Con coverage
pytest --cov=booking --cov-report=term-missing

# Objetivo de cobertura mínima:
# Services: 90%
# Views/API: 80%
# Models: 70%
```
