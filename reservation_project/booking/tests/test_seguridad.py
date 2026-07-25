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
        """Ni siquiera el dueño puede confirmar su reserva desde la URL."""
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'MP')
        assert reserva.estado_pago == EstadoPago.PENDIENTE

        client.force_login(user_t1)
        response = client.get(f'/success/{reserva.id}/?status=approved')

        assert response.status_code == 200          # el dueño ve su página
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
class TestIDORReservas:
    """Auditoría (2ª pasada): /success/<id>/ exponía reservas ajenas por ID."""

    def test_anonimo_no_ve_reserva_ajena(self, client, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'MP')
        assert client.get(f'/success/{reserva.id}/').status_code == 404

    def test_otro_usuario_no_ve_reserva_ajena(self, client, user_t1, user_t2, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'MP')
        client.force_login(user_t2)
        assert client.get(f'/success/{reserva.id}/').status_code == 404

    def test_el_dueno_si_ve_su_reserva(self, client, user_t1, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'MP')
        client.force_login(user_t1)
        assert client.get(f'/success/{reserva.id}/').status_code == 200

    def test_staff_ve_cualquier_reserva(self, client, user_t1, user_t2, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'MP')
        user_t2.is_staff = True
        user_t2.save(update_fields=['is_staff'])
        client.force_login(user_t2)
        assert client.get(f'/success/{reserva.id}/').status_code == 200

    def test_no_se_generan_preferencias_de_pago_ajenas(self, client, user_t1, user_t2, drop_activo):
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'MP')
        client.force_login(user_t2)
        assert client.get(f'/create-preference/{reserva.id}/').status_code == 404


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


@pytest.mark.django_db
class TestIntegridadDeCreditos:
    """Auditoría #8: aplicar más créditos que el total quemaba el excedente."""

    def test_no_quema_creditos_por_encima_del_total(self, user_t1, drop_activo, credit_balance):
        from decimal import Decimal

        credit_balance.balance_usd = Decimal('500.00')
        credit_balance.save()

        # Compra de 1 token = $100, intentando aplicar $500
        reserva = crear_reserva_pendiente(
            drop_activo.proyecto_id, user_t1, 1, 'CREDITO',
            creditos_aplicar=Decimal('500.00'),
        )

        credit_balance.refresh_from_db()
        assert reserva.total == Decimal('0.00')
        assert credit_balance.balance_usd == Decimal('400.00'), (
            'Se consumieron créditos por encima del precio de la compra'
        )

    def test_aplicacion_parcial_normal_sigue_funcionando(self, user_t1, drop_activo, credit_balance):
        from decimal import Decimal

        credit_balance.balance_usd = Decimal('500.00')
        credit_balance.save()

        reserva = crear_reserva_pendiente(
            drop_activo.proyecto_id, user_t1, 3, 'MP',       # $300
            creditos_aplicar=Decimal('100.00'),
        )

        credit_balance.refresh_from_db()
        assert reserva.total == Decimal('200.00')
        assert credit_balance.balance_usd == Decimal('400.00')


@pytest.mark.django_db
class TestIdempotenciaDeCompra:
    """Auditoría #10: doble click creaba 2 reservas y descontaba stock 2 veces."""

    def test_doble_click_no_duplica_la_reserva(self, user_t1, drop_activo):
        from booking.models import Reserva

        primera = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'MP')
        segunda = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'MP')

        assert primera.id == segunda.id
        assert Reserva.objects.filter(user=user_t1).count() == 1
        drop_activo.refresh_from_db()
        assert drop_activo.stock_disponible == 48, 'El stock se descontó dos veces'

    def test_compra_distinta_si_crea_reserva_nueva(self, user_t1, drop_activo):
        from booking.models import Reserva

        crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'MP')
        crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 3, 'MP')   # cantidad distinta

        assert Reserva.objects.filter(user=user_t1).count() == 2
        drop_activo.refresh_from_db()
        assert drop_activo.stock_disponible == 45


@pytest.mark.django_db
class TestExpiracionDeReservas:
    """Auditoría #9: las reservas abandonadas retenían stock para siempre."""

    def test_reserva_vencida_libera_stock(self, user_t1, drop_activo):
        from datetime import timedelta

        from django.utils import timezone

        from booking.models import Reserva
        from booking.services import expirar_reservas_pendientes

        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 5, 'MP')
        drop_activo.refresh_from_db()
        assert drop_activo.stock_disponible == 45

        # Envejecer la reserva por encima del timeout
        Reserva.objects.filter(id=reserva.id).update(
            created_at=timezone.now() - timedelta(minutes=200)
        )

        assert expirar_reservas_pendientes() == 1

        drop_activo.refresh_from_db()
        reserva.refresh_from_db()
        assert drop_activo.stock_disponible == 50, 'El stock no se liberó'
        assert reserva.estado_pago == EstadoPago.RECHAZADO

    def test_no_expira_reservas_recientes(self, user_t1, drop_activo):
        from booking.services import expirar_reservas_pendientes

        crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 5, 'MP')
        assert expirar_reservas_pendientes() == 0
        drop_activo.refresh_from_db()
        assert drop_activo.stock_disponible == 45

    def test_no_expira_reservas_confirmadas(self, user_t1, drop_activo):
        from datetime import timedelta

        from django.utils import timezone

        from booking.models import Reserva
        from booking.services import confirmar_reserva, expirar_reservas_pendientes

        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 5, 'MP')
        confirmar_reserva(reserva.id)
        Reserva.objects.filter(id=reserva.id).update(
            created_at=timezone.now() - timedelta(minutes=200)
        )

        assert expirar_reservas_pendientes() == 0
        reserva.refresh_from_db()
        assert reserva.estado_pago == EstadoPago.CONFIRMADO


@pytest.mark.django_db
class TestEndurecimiento:
    """Auditoría #4-#5-#12-#13 de la 2ª pasada: controles de acceso y rastro."""

    def test_registro_rechaza_password_debil(self, client):
        for debil in ['12345678', 'password', 'abcdefgh']:
            response = client.post(
                '/api/v1/auth/registro/',
                data=json.dumps({'email': f'x{debil}@test.cl', 'password': debil}),
                content_type='application/json',
            )
            assert response.status_code == 400, f'Se aceptó la contraseña débil: {debil}'

    def test_registro_acepta_password_fuerte(self, client):
        response = client.post(
            '/api/v1/auth/registro/',
            data=json.dumps({'email': 'fuerte@test.cl', 'password': 'Patagonia-2026-Rwa'}),
            content_type='application/json',
        )
        assert response.status_code == 201

    def test_cambio_de_tier_queda_auditado(self, client):
        from django.contrib.auth.models import Group

        from booking.models import AuditLog, TierConfig

        from .factories import UserFactory

        joan = UserFactory()
        grupo, _ = Group.objects.get_or_create(name='JoanAdmin')
        joan.groups.add(grupo)

        login = client.post(
            '/api/v1/auth/login/',
            data=json.dumps({'username': joan.username, 'password': 'testpass123'}),
            content_type='application/json',
        )
        headers = {'HTTP_AUTHORIZATION': f"Bearer {login.json()['access']}"}

        tier = TierConfig.objects.get(tier=1)
        client.put(
            f'/api/v1/admin/tiers/{tier.id}/',
            data=json.dumps({'nombre': 'Bronze', 'cap_creditos_usd': '9999.00',
                             'descuento_fees_pct': '7.50', 'descuento_creditos_pct': '10.00',
                             'kyc_requerido': 'lite'}),
            content_type='application/json',
            **headers,
        )

        log = AuditLog.objects.filter(accion='tier.modificado').first()
        assert log is not None, 'Un cambio de dinero no dejó rastro en AuditLog'
        assert log.user_id == joan.id
        assert log.datos_antes['cap_creditos_usd'] != log.datos_despues['cap_creditos_usd']

    def test_cupones_tienen_limite_por_ip(self, client, db):
        respuestas = [
            client.post('/validate-coupon/',
                        data=json.dumps({'code': f'FUERZA{i}'}),
                        content_type='application/json').status_code
            for i in range(25)
        ]
        assert 429 in respuestas, 'Se permite fuerza bruta sobre los códigos de cupón'
