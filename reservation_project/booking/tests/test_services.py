import threading
from decimal import Decimal

import pytest
from django.db import connection

from booking.constants import EstadoPago
from booking.exceptions import (
    DropInactivo,
    IdempotenciaError,
    LimiteKYCSuperado,
    StockInsuficiente,
)
from booking.services import (
    confirmar_reserva,
    crear_reserva_pendiente,
    marcar_reserva_fallida,
    validar_compra,
)

from .factories import DropFactory, ProyectoFactory


@pytest.mark.django_db
class TestValidarCompra:

    def test_sin_drop_activo_lanza_drop_inactivo(self, user_t1, proyecto_activo):
        with pytest.raises(DropInactivo):
            validar_compra(proyecto_activo.id, user_t1, 1, 'MP')

    def test_drop_inactivo_flag_lanza_drop_inactivo(self, user_t1, proyecto_activo):
        DropFactory(proyecto=proyecto_activo, activo=False)
        with pytest.raises(DropInactivo):
            validar_compra(proyecto_activo.id, user_t1, 1, 'MP')

    def test_stock_insuficiente(self, user_t1, drop_activo):
        with pytest.raises(StockInsuficiente):
            validar_compra(drop_activo.proyecto_id, user_t1, 51, 'MP')

    def test_limite_kyc_superado(self, user_t1, drop_activo):
        # T1 Bronze: límite $1.000. 11 tokens × $100 = $1.100
        with pytest.raises(LimiteKYCSuperado):
            validar_compra(drop_activo.proyecto_id, user_t1, 11, 'MP')

    def test_compra_valida_devuelve_drop_y_total(self, user_t1, drop_activo):
        drop, total = validar_compra(drop_activo.proyecto_id, user_t1, 5, 'MP')
        assert drop.id == drop_activo.id
        assert total == Decimal('500.00')

    def test_precio_override_del_drop_manda(self, user_t1, proyecto_activo):
        DropFactory(proyecto=proyecto_activo, precio_override=Decimal('80.00'))
        drop, total = validar_compra(proyecto_activo.id, user_t1, 5, 'MP')
        assert total == Decimal('400.00')


@pytest.mark.django_db
class TestCrearReservaPendiente:

    def test_crea_reserva_y_descuenta_stock(self, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 5, 'MP')
        drop_activo.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.PENDIENTE
        assert reserva.total == Decimal('500.00')
        assert drop_activo.stock_disponible == 45

    def test_stock_no_alcanza_no_crea_reserva(self, user_t1, drop_activo):
        with pytest.raises(StockInsuficiente):
            crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 51, 'MP')
        drop_activo.refresh_from_db()
        assert drop_activo.stock_disponible == 50


@pytest.mark.django_db
class TestConfirmarReserva:

    def test_confirma_y_actualiza_contadores(self, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 5, 'MP')
        confirmada = confirmar_reserva(reserva.id)

        assert confirmada.estado_pago == EstadoPago.CONFIRMADO
        proyecto = drop_activo.proyecto
        proyecto.refresh_from_db()
        assert proyecto.tokens_vendidos == 5
        user_t1.profile.refresh_from_db()
        assert user_t1.profile.investment_total_usd == Decimal('500.00')

    def test_es_idempotente(self, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 5, 'MP')
        confirmar_reserva(reserva.id)
        with pytest.raises(IdempotenciaError):
            confirmar_reserva(reserva.id)

    def test_no_recalcula_total_con_precio_override(self, user_t1, proyecto_activo):
        DropFactory(proyecto=proyecto_activo, precio_override=Decimal('80.00'))
        reserva = crear_reserva_pendiente(proyecto_activo.id, user_t1, 5, 'MP')
        confirmada = confirmar_reserva(reserva.id)
        assert confirmada.total == Decimal('400.00')


@pytest.mark.django_db
class TestMarcarReservaFallida:

    def test_devuelve_stock_al_drop(self, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 5, 'MP')
        drop_activo.refresh_from_db()
        assert drop_activo.stock_disponible == 45

        marcar_reserva_fallida(reserva.id, EstadoPago.FALLIDO, 'wrong_amount')
        drop_activo.refresh_from_db()
        assert drop_activo.stock_disponible == 50
        reserva.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.FALLIDO

    def test_confirmada_no_se_puede_marcar_fallida(self, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 5, 'MP')
        confirmar_reserva(reserva.id)
        with pytest.raises(IdempotenciaError):
            marcar_reserva_fallida(reserva.id, EstadoPago.FALLIDO)


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(
    connection.vendor == 'sqlite',
    reason='select_for_update requiere PostgreSQL — correr con DATABASE_URL de Postgres',
)
def test_race_condition_stock_no_vende_mas_del_disponible(user_t1, drop_activo):
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
        finally:
            connection.close()

    t1 = threading.Thread(target=intentar_compra)
    t2 = threading.Thread(target=intentar_compra)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(resultados) == 1, f"Esperado 1 éxito, obtenido {len(resultados)}"
    assert len(errores) == 1, f"Esperado 1 error, obtenido {len(errores)}"

    drop_activo.refresh_from_db()
    assert drop_activo.stock_disponible == 0
