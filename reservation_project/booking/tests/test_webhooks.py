import json

import pytest

from booking.constants import EstadoPago
from booking.integrations.cryptomus import generar_firma_para_test
from booking.services import confirmar_reserva, crear_reserva_pendiente

TEST_API_KEY = 'test-cryptomus-key'


def _post_webhook_cryptomus(client, payload: dict):
    """Firma el payload como lo haría Cryptomus y hace el POST."""
    payload = dict(payload)
    payload['sign'] = generar_firma_para_test({k: v for k, v in payload.items() if k != 'sign'})
    return client.post(
        '/api/webhooks/cryptomus/',
        data=json.dumps(payload),
        content_type='application/json',
    )


@pytest.mark.django_db
class TestCryptomusWebhook:

    @pytest.fixture(autouse=True)
    def _api_key_de_test(self, settings):
        settings.CRYPTOMUS_PAYMENT_API_KEY = TEST_API_KEY

    def test_firma_invalida_403(self, client):
        response = client.post(
            '/api/webhooks/cryptomus/',
            data=json.dumps({'status': 'paid', 'order_id': '1', 'sign': 'invalida', 'is_final': True}),
            content_type='application/json',
        )
        assert response.status_code == 403

    def test_sin_firma_403(self, client):
        response = client.post(
            '/api/webhooks/cryptomus/',
            data=json.dumps({'status': 'paid', 'order_id': '1', 'is_final': True}),
            content_type='application/json',
        )
        assert response.status_code == 403

    def test_paid_confirma_reserva(self, client, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'CRYPTO')
        response = _post_webhook_cryptomus(client, {
            'status': 'paid',
            'uuid': 'uuid-test-1',
            'order_id': str(reserva.id),
            'is_final': True,
        })
        assert response.status_code == 200
        reserva.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.CONFIRMADO
        assert reserva.cryptomus_uuid == 'uuid-test-1'

    def test_webhook_duplicado_200_sin_cambios(self, client, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'CRYPTO')
        payload = {
            'status': 'paid',
            'uuid': 'uuid-test-2',
            'order_id': str(reserva.id),
            'is_final': True,
        }
        assert _post_webhook_cryptomus(client, payload).status_code == 200
        # Segundo POST idéntico
        assert _post_webhook_cryptomus(client, payload).status_code == 200
        reserva.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.CONFIRMADO

    def test_wrong_amount_falla_y_devuelve_stock(self, client, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 5, 'CRYPTO')
        drop_activo.refresh_from_db()
        assert drop_activo.stock_disponible == 45

        response = _post_webhook_cryptomus(client, {
            'status': 'wrong_amount',
            'uuid': 'uuid-test-3',
            'order_id': str(reserva.id),
            'is_final': True,
        })
        assert response.status_code == 200
        reserva.refresh_from_db()
        drop_activo.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.FALLIDO
        assert drop_activo.stock_disponible == 50

    def test_cancel_devuelve_stock(self, client, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 3, 'CRYPTO')
        response = _post_webhook_cryptomus(client, {
            'status': 'cancel',
            'uuid': 'uuid-test-4',
            'order_id': str(reserva.id),
            'is_final': True,
        })
        assert response.status_code == 200
        drop_activo.refresh_from_db()
        assert drop_activo.stock_disponible == 50
        reserva.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.RECHAZADO

    def test_is_final_false_no_procesa(self, client, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'CRYPTO')
        response = _post_webhook_cryptomus(client, {
            'status': 'process',
            'uuid': 'uuid-test-5',
            'order_id': str(reserva.id),
            'is_final': False,
        })
        assert response.status_code == 200
        reserva.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.PENDIENTE

    def test_paid_over_confirma_y_audita_excedente(self, client, user_t1, drop_activo):
        from booking.models import AuditLog
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'CRYPTO')
        response = _post_webhook_cryptomus(client, {
            'status': 'paid_over',
            'uuid': 'uuid-test-6',
            'order_id': str(reserva.id),
            'is_final': True,
        })
        assert response.status_code == 200
        reserva.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.CONFIRMADO
        assert AuditLog.objects.filter(accion='pago.excedente', objeto_id=reserva.id).exists()

    def test_reserva_confirmada_no_se_puede_fallar_por_webhook(self, client, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'CRYPTO')
        confirmar_reserva(reserva.id)
        response = _post_webhook_cryptomus(client, {
            'status': 'wrong_amount',
            'uuid': 'uuid-test-7',
            'order_id': str(reserva.id),
            'is_final': True,
        })
        assert response.status_code == 200
        reserva.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.CONFIRMADO  # sin cambios


@pytest.mark.django_db
class TestMPWebhook:

    def test_firma_invalida_403(self, client, settings):
        settings.MERCADOPAGO_WEBHOOK_SECRET = 'test-mp-secret'
        response = client.post(
            '/api/webhooks/mp/',
            data=json.dumps({'type': 'payment', 'data': {'id': '12345'}}),
            content_type='application/json',
            HTTP_X_SIGNATURE='ts=fake,v1=invalida',
        )
        assert response.status_code == 403

    def test_sin_secret_configurado_403(self, client, settings):
        settings.MERCADOPAGO_WEBHOOK_SECRET = ''
        response = client.post(
            '/api/webhooks/mp/',
            data=json.dumps({'type': 'payment', 'data': {'id': '12345'}}),
            content_type='application/json',
        )
        assert response.status_code == 403

    def test_firma_valida_delega_a_task(self, client, settings, mocker):
        settings.MERCADOPAGO_WEBHOOK_SECRET = 'test-mp-secret'
        import hashlib
        import hmac as hmac_mod

        mock_task = mocker.patch('booking.tasks.procesar_pago_mp_task.delay')

        data_id = '99887'
        request_id = 'req-abc'
        ts = '1704908010'
        # Template oficial de MP: id + request-id + ts
        manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
        v1 = hmac_mod.new(b'test-mp-secret', manifest.encode(), hashlib.sha256).hexdigest()

        response = client.post(
            '/api/webhooks/mp/',
            data=json.dumps({'type': 'payment', 'data': {'id': data_id}}),
            content_type='application/json',
            HTTP_X_REQUEST_ID=request_id,
            HTTP_X_SIGNATURE=f'ts={ts},v1={v1}',
        )
        assert response.status_code == 200
        mock_task.assert_called_once_with(data_id)


@pytest.mark.django_db
class TestKushkiWebhook:

    def test_sin_firma_403(self, client):
        response = client.post(
            '/api/webhooks/kushki/',
            data=json.dumps({'status': 'approved', 'metadata': {'reserva_id': '1'}}),
            content_type='application/json',
        )
        assert response.status_code == 403

    def test_firma_valida_confirma(self, client, settings, user_t1, drop_activo):
        settings.KUSHKI_PRIVATE_KEY = 'test-kushki-key'
        import hashlib
        import hmac as hmac_mod

        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'KUSHKI')
        body = json.dumps({'status': 'approved', 'metadata': {'reserva_id': str(reserva.id)}}).encode()
        firma = hmac_mod.new(b'test-kushki-key', body, hashlib.sha256).hexdigest()

        response = client.post(
            '/api/webhooks/kushki/',
            data=body,
            content_type='application/json',
            HTTP_X_KUSHKI_SIGNATURE=firma,
        )
        assert response.status_code == 200
        reserva.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.CONFIRMADO
