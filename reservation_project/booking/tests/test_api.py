import json
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from booking.constants import EstadoPago
from booking.models import CreditBalance, FraccionadorProfile, TierConfig

from .factories import DropFactory, ProyectoFactory, UserFactory


def _auth_headers(client, user, password='testpass123'):
    """Login por API y devuelve headers con Bearer token."""
    response = client.post(
        '/api/v1/auth/login/',
        data=json.dumps({'username': user.username, 'password': password}),
        content_type='application/json',
    )
    assert response.status_code == 200, response.content
    tokens = response.json()
    return {'HTTP_AUTHORIZATION': f"Bearer {tokens['access']}"}, tokens


# ── Públicos ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEndpointsPublicos:

    def test_proyectos_list(self, client, proyecto_activo):
        response = client.get('/api/v1/proyectos/')
        assert response.status_code == 200
        nombres = [p['nombre'] for p in response.json()['results']]
        assert proyecto_activo.nombre in nombres

    def test_proyecto_detail_por_slug(self, client, proyecto_activo):
        response = client.get(f'/api/v1/proyectos/{proyecto_activo.slug}/')
        assert response.status_code == 200
        assert response.json()['slug'] == proyecto_activo.slug

    def test_proyecto_drop_activo(self, client, drop_activo):
        slug = drop_activo.proyecto.slug
        response = client.get(f'/api/v1/proyectos/{slug}/drop/')
        assert response.status_code == 200
        assert response.json()['stock_disponible'] == 50

    def test_proyecto_sin_drop_404(self, client, proyecto_activo):
        response = client.get(f'/api/v1/proyectos/{proyecto_activo.slug}/drop/')
        assert response.status_code == 404
        assert response.json()['error'] == 'drop_inactivo'

    def test_tiers_publicos(self, client, db):
        response = client.get('/api/v1/tiers/')
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        assert data[0]['nombre'] == 'Bronze'

    def test_fees_publicos(self, client, db):
        response = client.get('/api/v1/fees/')
        assert response.status_code == 200
        assert len(response.json()) == 5


# ── Auth ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAuth:

    def test_login_devuelve_tokens(self, client, user_t1):
        _, tokens = _auth_headers(client, user_t1)
        assert 'access' in tokens and 'refresh' in tokens

    def test_login_password_incorrecta_401(self, client, user_t1):
        response = client.post(
            '/api/v1/auth/login/',
            data=json.dumps({'username': user_t1.username, 'password': 'mala'}),
            content_type='application/json',
        )
        assert response.status_code == 401

    def test_refresh(self, client, user_t1):
        _, tokens = _auth_headers(client, user_t1)
        response = client.post(
            '/api/v1/auth/refresh/',
            data=json.dumps({'refresh': tokens['refresh']}),
            content_type='application/json',
        )
        assert response.status_code == 200
        assert 'access' in response.json()

    def test_logout_blacklistea_refresh(self, client, user_t1):
        headers, tokens = _auth_headers(client, user_t1)
        response = client.post(
            '/api/v1/auth/logout/',
            data=json.dumps({'refresh': tokens['refresh']}),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 205
        # El refresh ya no sirve
        response = client.post(
            '/api/v1/auth/refresh/',
            data=json.dumps({'refresh': tokens['refresh']}),
            content_type='application/json',
        )
        assert response.status_code == 401

    def test_registro_crea_usuario_con_perfil(self, client, db):
        response = client.post(
            '/api/v1/auth/registro/',
            data=json.dumps({'email': 'nuevo@test.cl', 'password': 'clave-segura-9'}),
            content_type='application/json',
        )
        assert response.status_code == 201
        assert 'access' in response.json()
        from django.contrib.auth.models import User
        user = User.objects.get(email='nuevo@test.cl')
        assert user.profile.kyc_tier == 1  # signal creó el perfil

    def test_registro_email_duplicado_400(self, client, user_t1):
        response = client.post(
            '/api/v1/auth/registro/',
            data=json.dumps({'email': user_t1.email, 'password': 'clave-segura-9'}),
            content_type='application/json',
        )
        assert response.status_code == 400

    def test_password_reset_no_revela_emails(self, client, db):
        response = client.post(
            '/api/v1/auth/password/reset/',
            data=json.dumps({'email': 'noexiste@test.cl'}),
            content_type='application/json',
        )
        assert response.status_code == 200


# ── Inversor ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestInversor:

    def test_endpoints_requieren_auth(self, client, db):
        for url in ['/api/v1/mis-inversiones/', '/api/v1/mis-creditos/', '/api/v1/perfil/']:
            assert client.get(url).status_code == 401

    def test_comprar_flujo_completo_mp(self, client, user_t1, drop_activo):
        headers, _ = _auth_headers(client, user_t1)
        response = client.post(
            '/api/v1/comprar/',
            data=json.dumps({
                'proyecto_id': drop_activo.proyecto_id,
                'cantidad_tokens': 3,
                'metodo_pago': 'MP',
            }),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 201, response.content
        data = response.json()
        assert data['reserva']['estado_pago'] == EstadoPago.PENDIENTE
        assert data['pago']['metodo'] == 'MP'
        drop_activo.refresh_from_db()
        assert drop_activo.stock_disponible == 47

    def test_comprar_sin_drop_404(self, client, user_t1, proyecto_activo):
        headers, _ = _auth_headers(client, user_t1)
        response = client.post(
            '/api/v1/comprar/',
            data=json.dumps({
                'proyecto_id': proyecto_activo.id,
                'cantidad_tokens': 1,
                'metodo_pago': 'MP',
            }),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 404
        assert response.json()['error'] == 'drop_inactivo'

    def test_comprar_stock_insuficiente_409(self, client, user_t1, drop_activo):
        # T4 para no chocar con el límite KYC antes que con el stock
        perfil = user_t1.profile
        perfil.kyc_tier = 4
        perfil.save()

        headers, _ = _auth_headers(client, user_t1)
        response = client.post(
            '/api/v1/comprar/',
            data=json.dumps({
                'proyecto_id': drop_activo.proyecto_id,
                'cantidad_tokens': 51,
                'metodo_pago': 'MP',
            }),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 409
        assert response.json()['error'] == 'stock_insuficiente'

    def test_middleware_bloquea_compra_jwt_sobre_limite(self, client, user_t1, drop_activo):
        perfil = user_t1.profile
        perfil.investment_total_usd = Decimal('1000.00')
        perfil.save()

        headers, _ = _auth_headers(client, user_t1)
        response = client.post(
            '/api/v1/comprar/',
            data=json.dumps({
                'proyecto_id': drop_activo.proyecto_id,
                'cantidad_tokens': 1,
                'metodo_pago': 'MP',
            }),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 403
        assert response.json()['error'] == 'limite_kyc_superado'

    def test_comprar_100pct_con_creditos_confirma(self, client, user_t1, drop_activo, credit_balance):
        credit_balance.balance_usd = Decimal('500.00')
        credit_balance.save()

        headers, _ = _auth_headers(client, user_t1)
        response = client.post(
            '/api/v1/comprar/',
            data=json.dumps({
                'proyecto_id': drop_activo.proyecto_id,
                'cantidad_tokens': 5,          # 5 × $100 = $500
                'metodo_pago': 'CREDITO',
                'creditos_aplicar': '500.00',
            }),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 201, response.content
        data = response.json()
        assert data['reserva']['estado_pago'] == EstadoPago.CONFIRMADO
        credit_balance.refresh_from_db()
        assert credit_balance.balance_usd == Decimal('0.00')

    def test_mis_creditos_y_compra_de_creditos(self, client, user_t1):
        headers, _ = _auth_headers(client, user_t1)

        response = client.post(
            '/api/v1/creditos/comprar/',
            data=json.dumps({'monto_usd': '500.00', 'metodo_pago': 'MP'}),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 200
        assert response.json()['precio_a_pagar'] == '450.00'  # 10% off T1

        response = client.get('/api/v1/mis-creditos/', **headers)
        assert response.status_code == 200

    def test_mis_inversiones_solo_las_propias(self, client, user_t1, user_t2, drop_activo):
        from booking.services import crear_reserva_pendiente
        crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 2, 'MP')
        crear_reserva_pendiente(drop_activo.proyecto_id, user_t2, 3, 'MP')

        headers, _ = _auth_headers(client, user_t1)
        response = client.get('/api/v1/mis-inversiones/', **headers)
        data = response.json()['results']
        assert len(data) == 1
        assert data[0]['cantidad_tokens'] == 2

    def test_perfil_get_y_put(self, client, user_t1):
        headers, _ = _auth_headers(client, user_t1)
        response = client.get('/api/v1/perfil/', **headers)
        assert response.status_code == 200

        response = client.put(
            '/api/v1/perfil/',
            data=json.dumps({'telefono': '+56911112222', 'first_name': 'Test'}),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 200
        assert response.json()['telefono'] == '+56911112222'


# ── Fraccionador ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestFraccionador:

    @pytest.fixture
    def fraccionador(self, db):
        user = UserFactory()
        grupo, _ = Group.objects.get_or_create(name='Fractionalizer')
        user.groups.add(grupo)
        return user

    def test_usuario_normal_no_accede_403(self, client, user_t1):
        headers, _ = _auth_headers(client, user_t1)
        response = client.get('/api/v1/fraccionador/proyectos/', **headers)
        assert response.status_code == 403

    def test_crear_y_listar_proyectos_propios(self, client, fraccionador):
        headers, _ = _auth_headers(client, fraccionador)
        response = client.post(
            '/api/v1/fraccionador/proyectos/',
            data=json.dumps({
                'nombre': 'Campo Los Coigües',
                'descripcion': 'Terreno con bosque nativo',
                'ubicacion': 'Los Lagos',
                'precio_token': '120.00',
                'tokens_totales': 500,
            }),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 201, response.content
        data = response.json()
        assert data['slug'] == 'campo-los-coigues'  # autogenerado

        response = client.get('/api/v1/fraccionador/proyectos/', **headers)
        assert len(response.json()['results']) == 1

    def test_no_puede_ver_proyecto_ajeno(self, client, fraccionador):
        ajeno = ProyectoFactory()  # owner distinto
        headers, _ = _auth_headers(client, fraccionador)
        response = client.get(f'/api/v1/fraccionador/proyectos/{ajeno.id}/', **headers)
        assert response.status_code == 404

    def test_crear_drop_de_su_proyecto(self, client, fraccionador):
        proyecto = ProyectoFactory(owner=fraccionador)
        headers, _ = _auth_headers(client, fraccionador)
        response = client.post(
            '/api/v1/fraccionador/drops/',
            data=json.dumps({
                'proyecto': proyecto.id,
                'nombre': 'Drop 1',
                'numero': 1,
                'stock_total': 150,
                'stock_disponible': 150,
                'fecha_inicio': '2026-07-01T00:00:00Z',
                'fecha_fin': '2026-08-01T00:00:00Z',
                'activo': True,
            }),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 201, response.content

    def test_no_puede_crear_drop_en_proyecto_ajeno(self, client, fraccionador):
        ajeno = ProyectoFactory()
        headers, _ = _auth_headers(client, fraccionador)
        response = client.post(
            '/api/v1/fraccionador/drops/',
            data=json.dumps({
                'proyecto': ajeno.id,
                'nombre': 'Drop 1',
                'numero': 1,
                'stock_total': 150,
                'stock_disponible': 150,
                'fecha_inicio': '2026-07-01T00:00:00Z',
                'fecha_fin': '2026-08-01T00:00:00Z',
            }),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 400


# ── Admin Joan ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAdminJoan:

    @pytest.fixture
    def joan(self, db):
        user = UserFactory()
        grupo, _ = Group.objects.get_or_create(name='JoanAdmin')
        user.groups.add(grupo)
        return user

    def test_usuario_normal_403(self, client, user_t1):
        headers, _ = _auth_headers(client, user_t1)
        assert client.get('/api/v1/admin/proyectos/', **headers).status_code == 403

    def test_editar_tier(self, client, joan):
        tier = TierConfig.objects.get(tier=1)
        headers, _ = _auth_headers(client, joan)
        response = client.put(
            f'/api/v1/admin/tiers/{tier.id}/',
            data=json.dumps({'nombre': 'Bronze', 'cap_creditos_usd': '1500.00',
                             'descuento_fees_pct': '7.50', 'descuento_creditos_pct': '10.00',
                             'kyc_requerido': 'lite'}),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 200, response.content
        tier.refresh_from_db()
        assert tier.cap_creditos_usd == Decimal('1500.00')

    def test_aprobar_fraccionador(self, client, joan):
        candidato = UserFactory()
        perfil = FraccionadorProfile.objects.create(user=candidato)
        headers, _ = _auth_headers(client, joan)

        response = client.post(
            f'/api/v1/admin/fraccionadores/{perfil.id}/aprobar/',
            data=json.dumps({'notas': 'Documentación OK'}),
            content_type='application/json',
            **headers,
        )
        assert response.status_code == 200
        perfil.refresh_from_db()
        assert perfil.kyb_estado == 'APROBADO'
        assert candidato.groups.filter(name='Fractionalizer').exists()

    def test_auditlog_listado(self, client, joan, user_t1, drop_activo):
        from booking.services import confirmar_reserva, crear_reserva_pendiente
        reserva = crear_reserva_pendiente(drop_activo.proyecto_id, user_t1, 1, 'MP')
        confirmar_reserva(reserva.id)

        headers, _ = _auth_headers(client, joan)
        response = client.get('/api/v1/admin/auditlog/?accion=reserva.confirmada', **headers)
        assert response.status_code == 200
        assert len(response.json()['results']) == 1
