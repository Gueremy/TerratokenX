import pytest


@pytest.fixture(autouse=True)
def _limpiar_cache():
    """Evita que throttles y selectors cacheados contaminen entre tests."""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


from .factories import (  # noqa: E402
    CreditBalanceFactory,
    DropFactory,
    ProyectoFactory,
    ReservaFactory,
    UserFactory,
    UserProfileFactory,
)


def _user_con_tier(tier: int):
    """El signal post_save ya crea el perfil — solo hay que ajustar el tier."""
    user = UserFactory()
    perfil = user.profile
    perfil.kyc_tier = tier
    perfil.save(update_fields=['kyc_tier'])
    return user


@pytest.fixture
def user_t1(db):
    return _user_con_tier(1)


@pytest.fixture
def user_t2(db):
    return _user_con_tier(2)


@pytest.fixture
def user_t4(db):
    return _user_con_tier(4)


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
def credit_balance(db, user_t1):
    return CreditBalanceFactory(user=user_t1)
