"""Tests de regresión de seguridad.

Cada test aquí corresponde a una vulnerabilidad encontrada en auditoría.
Si alguno falla, la vulnerabilidad volvió.
"""

import io
import json

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from booking.constants import EstadoPago
from booking.services import crear_reserva_pendiente


@pytest.mark.django_db
class TestBypassDePago:
    """Auditoría #1: /success/<id>/?status=approved confirmaba reservas sin pagar."""

    def test_query_param_approved_no_confirma_reserva(self, client, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'MP')
        assert reserva.estado_pago == EstadoPago.PENDIENTE

        response = client.get(f'/success/{reserva.id}/?status=approved')

        assert response.status_code == 200          # la página se muestra
        reserva.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.PENDIENTE, (
            'BYPASS DE PAGO: el query param confirmó la reserva'
        )

    def test_no_contamina_contadores_financieros(self, user_t1, drop_activo, client):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 3, 'MP')
        proyecto = drop_activo.proyecto

        client.get(f'/success/{reserva.id}/?status=approved')

        proyecto.refresh_from_db()
        user_t1.profile.refresh_from_db()
        assert proyecto.tokens_vendidos == 0
        assert user_t1.profile.investment_total_usd == 0

    def test_usuario_anonimo_no_puede_confirmar_reserva_ajena(self, client, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 1, 'MP')

        # Sin autenticación, iterando IDs
        client.get(f'/success/{reserva.id}/?status=approved')
        client.get(f'/success/{reserva.id}/?status=success')
        client.get(f'/success/{reserva.id}/?status=CONFIRMADO')

        reserva.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.PENDIENTE


@pytest.mark.django_db
class TestValidacionDeArchivos:
    """Auditoría #4: los campos de KYC/KYB aceptaban cualquier archivo."""

    def test_rechaza_tipo_no_permitido(self):
        from booking.validators import validar_archivo_kyc

        archivo = SimpleUploadedFile('malicioso.html', b'<script>alert(1)</script>',
                                     content_type='text/html')
        with pytest.raises(ValidationError):
            validar_archivo_kyc(archivo)

    def test_rechaza_archivo_muy_grande(self):
        from booking.validators import MAX_FILE_SIZE_MB, validar_archivo_kyc

        grande = SimpleUploadedFile(
            'grande.pdf',
            b'x' * (MAX_FILE_SIZE_MB * 1024 * 1024 + 1),
            content_type='application/pdf',
        )
        with pytest.raises(ValidationError):
            validar_archivo_kyc(grande)

    def test_acepta_pdf_valido(self):
        from booking.validators import validar_archivo_kyc

        ok = SimpleUploadedFile('cedula.pdf', b'%PDF-1.4 contenido',
                                content_type='application/pdf')
        validar_archivo_kyc(ok)  # no debe lanzar

    def test_nombre_de_archivo_no_permite_path_traversal(self):
        from booking.validators import nombre_seguro

        nombre = nombre_seguro('../../../etc/passwd.pdf')
        assert '/' not in nombre and '..' not in nombre
        assert nombre.endswith('.pdf')

    def test_nombre_de_archivo_es_aleatorio(self):
        from booking.validators import nombre_seguro

        assert nombre_seguro('foto.png') != nombre_seguro('foto.png')

    def test_vista_kyc_legacy_rechaza_html_malicioso(self, client, user_t1):
        """Los validators del modelo no corren en save(): la vista valida a mano."""
        client.force_login(user_t1)
        malicioso = SimpleUploadedFile('xss.html', b'<script>alert(1)</script>',
                                       content_type='text/html')

        client.post('/portal/kyc/', {'frontal': malicioso}, follow=True)

        user_t1.profile.refresh_from_db()
        assert not user_t1.profile.documento_identidad_frontal, (
            'Se guardó un HTML como documento de identidad'
        )

    def test_vista_kyc_legacy_acepta_imagen_valida(self, client, user_t1):
        client.force_login(user_t1)
        png = SimpleUploadedFile('cedula.png', b'\x89PNG\r\n\x1a\n' + b'0' * 100,
                                 content_type='image/png')

        client.post('/portal/kyc/', {'frontal': png}, follow=True)

        user_t1.profile.refresh_from_db()
        assert user_t1.profile.documento_identidad_frontal

    def test_archivo_guardado_no_conserva_el_nombre_original(self, client, user_t1):
        client.force_login(user_t1)
        png = SimpleUploadedFile('mi-cedula-secreta.png',
                                 b'\x89PNG\r\n\x1a\n' + b'0' * 100,
                                 content_type='image/png')

        client.post('/portal/kyc/', {'frontal': png}, follow=True)

        user_t1.profile.refresh_from_db()
        ruta = user_t1.profile.documento_identidad_frontal.name
        assert 'mi-cedula-secreta' not in ruta, f'El nombre original quedó expuesto: {ruta}'
        assert ruta.startswith('kyc/documentos/')


@pytest.mark.django_db
class TestFirmaMercadoPago:
    """Auditoría #5: el manifest omitía ts: y toda firma real de MP fallaba."""

    def test_firma_con_formato_real_de_mp_es_aceptada(self, client, settings, mocker):
        import hashlib
        import hmac

        settings.MERCADOPAGO_WEBHOOK_SECRET = 'secreto-mp'
        mock_task = mocker.patch('booking.tasks.procesar_pago_mp_task.delay')

        data_id = '1234567890'
        request_id = 'req-uuid-abc'
        ts = '1704908010'
        # Template oficial de MercadoPago
        manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
        v1 = hmac.new(b'secreto-mp', manifest.encode(), hashlib.sha256).hexdigest()

        response = client.post(
            '/api/webhooks/mp/',
            data=json.dumps({'type': 'payment', 'data': {'id': data_id}}),
            content_type='application/json',
            HTTP_X_REQUEST_ID=request_id,
            HTTP_X_SIGNATURE=f'ts={ts},v1={v1}',
        )

        assert response.status_code == 200, 'La firma real de MP fue rechazada'
        mock_task.assert_called_once_with(data_id)

    def test_firma_sin_ts_es_rechazada(self, client, settings):
        import hashlib
        import hmac

        settings.MERCADOPAGO_WEBHOOK_SECRET = 'secreto-mp'
        data_id = '1234567890'
        request_id = 'req-uuid-abc'
        # Manifest viejo (con el bug): sin ts
        manifest = f"id:{data_id};request-id:{request_id};"
        v1 = hmac.new(b'secreto-mp', manifest.encode(), hashlib.sha256).hexdigest()

        response = client.post(
            '/api/webhooks/mp/',
            data=json.dumps({'type': 'payment', 'data': {'id': data_id}}),
            content_type='application/json',
            HTTP_X_REQUEST_ID=request_id,
            HTTP_X_SIGNATURE=f'ts=1704908010,v1={v1}',
        )
        assert response.status_code == 403

    def test_ts_alterado_invalida_la_firma(self, client, settings):
        import hashlib
        import hmac

        settings.MERCADOPAGO_WEBHOOK_SECRET = 'secreto-mp'
        data_id = '99'
        request_id = 'req-1'
        manifest = f"id:{data_id};request-id:{request_id};ts:1000;"
        v1 = hmac.new(b'secreto-mp', manifest.encode(), hashlib.sha256).hexdigest()

        response = client.post(
            '/api/webhooks/mp/',
            data=json.dumps({'type': 'payment', 'data': {'id': data_id}}),
            content_type='application/json',
            HTTP_X_REQUEST_ID=request_id,
            HTTP_X_SIGNATURE=f'ts=9999,v1={v1}',   # ts distinto al firmado
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestEmailNoFallaEnSilencio:
    """Auditoría #6: sin RESEND_API_KEY los emails desaparecían sin error."""

    def test_produccion_sin_api_key_registra_error(self, settings, caplog):
        from booking.integrations import resend as resend_mod

        settings.RESEND_API_KEY = ''
        settings.DEBUG = False

        enviado = resend_mod._enviar('a@test.cl', 'Asunto', '<p>hola</p>')

        assert enviado is False
        assert any('resend' in r.message.lower() or 'api key' in r.message.lower()
                   for r in caplog.records), 'No se registró el error de configuración'

    def test_local_sin_api_key_usa_consola(self, settings):
        from django.core import mail

        from booking.integrations import resend as resend_mod

        settings.RESEND_API_KEY = ''
        settings.DEBUG = True

        assert resend_mod._enviar('a@test.cl', 'Asunto', '<p>hola</p>') is True
        assert len(mail.outbox) == 1
