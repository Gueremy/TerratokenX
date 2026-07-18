from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from booking.exceptions import CreditoInsuficiente, IdempotenciaError, LimiteKYCSuperado
from booking.models import CreditBalance, CreditTransaction
from booking.services_creditos import (
    acreditar_creditos,
    aplicar_credito_en_checkout,
    calcular_fee,
    calcular_precio_creditos,
    comprar_creditos,
    extender_expiracion_creditos,
)
from booking.tasks import expirar_creditos_vencidos

from .factories import CreditBalanceFactory


@pytest.mark.django_db
class TestCalcularFee:

    def test_fee_listing_t1(self, user_t1):
        # LISTING 1.5% de $1.000 = $15... pero mínimo $500 manda → $500 - 7.5% = $462.50
        assert calcular_fee(Decimal('1000'), 'LISTING', 1) == Decimal('462.50')

    def test_fee_transaccion_t1(self):
        # TRANSACCION 1.0% de $1.000 = $10.00 − 7.5% descuento = $9.25
        assert calcular_fee(Decimal('1000'), 'TRANSACCION', 1) == Decimal('9.25')

    def test_fee_transaccion_t4(self):
        # 1.0% de $1.000 = $10.00 − 31.5% = $6.85
        assert calcular_fee(Decimal('1000'), 'TRANSACCION', 4) == Decimal('6.85')

    def test_fee_siempre_decimal_dos_decimales(self):
        fee = calcular_fee(Decimal('333.33'), 'TRANSACCION', 2)
        assert isinstance(fee, Decimal)
        assert fee == fee.quantize(Decimal('0.01'))


@pytest.mark.django_db
class TestCalcularPrecioCreditos:

    def test_t1_paga_900_por_1000(self):
        assert calcular_precio_creditos(Decimal('1000'), 1) == Decimal('900.00')

    def test_t4_paga_600_por_1000(self):
        assert calcular_precio_creditos(Decimal('1000'), 4) == Decimal('600.00')


@pytest.mark.django_db
class TestComprarCreditos:

    def test_devuelve_precio_con_descuento(self, user_t1):
        resultado = comprar_creditos(user_t1, Decimal('500.00'), 'MP')
        assert resultado['precio_a_pagar'] == Decimal('450.00')
        assert resultado['descuento_aplicado'] == Decimal('50.00')

    def test_cap_del_tier_bloquea(self, user_t1):
        # Cap T1 Bronze: $1.000
        with pytest.raises(LimiteKYCSuperado):
            comprar_creditos(user_t1, Decimal('1001.00'), 'MP')


@pytest.mark.django_db
class TestAcreditarYAplicar:

    def test_acreditar_suma_al_balance(self, user_t1):
        acreditar_creditos(user_t1, Decimal('200.00'), 'Compra confirmada')
        balance = CreditBalance.objects.get(user=user_t1)
        assert balance.balance_usd == Decimal('200.00')
        assert CreditTransaction.objects.filter(user=user_t1, tipo='COMPRA').exists()

    def test_aplicar_descuenta_saldo(self, user_t1, credit_balance):
        descontado = aplicar_credito_en_checkout(user_t1, Decimal('40.00'))
        assert descontado == Decimal('40.00')
        credit_balance.refresh_from_db()
        assert credit_balance.balance_usd == Decimal('60.00')

    def test_aplicar_mas_que_balance_lanza_credito_insuficiente(self, user_t1, credit_balance):
        with pytest.raises(CreditoInsuficiente):
            aplicar_credito_en_checkout(user_t1, Decimal('100.01'))
        credit_balance.refresh_from_db()
        assert credit_balance.balance_usd == Decimal('100.00')  # sin cambios

    def test_balance_nunca_queda_negativo(self, user_t1, credit_balance):
        aplicar_credito_en_checkout(user_t1, Decimal('100.00'))
        credit_balance.refresh_from_db()
        assert credit_balance.balance_usd == Decimal('0.00')
        with pytest.raises(CreditoInsuficiente):
            aplicar_credito_en_checkout(user_t1, Decimal('0.01'))

    def test_creditos_vencidos_no_se_pueden_usar(self, user_t1):
        CreditBalanceFactory(user=user_t1, expires_at=timezone.now() - timedelta(days=1))
        with pytest.raises(CreditoInsuficiente):
            aplicar_credito_en_checkout(user_t1, Decimal('10.00'))


@pytest.mark.django_db
class TestExpiracion:

    def test_expirar_creditos_vencidos(self, user_t1):
        CreditBalanceFactory(user=user_t1, expires_at=timezone.now() - timedelta(days=1))
        resultado = expirar_creditos_vencidos()
        balance = CreditBalance.objects.get(user=user_t1)
        assert balance.balance_usd == Decimal('0.00')
        assert CreditTransaction.objects.filter(user=user_t1, tipo='EXPIRACION').exists()
        assert '1' in resultado

    def test_no_expira_vigentes(self, user_t1, credit_balance):
        expirar_creditos_vencidos()
        credit_balance.refresh_from_db()
        assert credit_balance.balance_usd == Decimal('100.00')

    def test_extension_solo_una_vez(self, user_t1, credit_balance):
        balance = extender_expiracion_creditos(user_t1)
        assert balance.extended is True
        with pytest.raises(IdempotenciaError):
            extender_expiracion_creditos(user_t1)
