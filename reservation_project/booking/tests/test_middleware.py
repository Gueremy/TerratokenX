from decimal import Decimal

import pytest


@pytest.mark.django_db
class TestKYCCheckMiddleware:

    def test_bloquea_post_comprar_si_limite_alcanzado(self, client, user_t1):
        perfil = user_t1.profile
        perfil.investment_total_usd = Decimal('1000.00')  # límite T1 Bronze
        perfil.save()

        client.force_login(user_t1)
        response = client.post('/api/v1/comprar/', data={}, content_type='application/json')

        assert response.status_code == 403
        data = response.json()
        assert data['error'] == 'limite_kyc_superado'
        assert data['tier_actual'] == 1

    def test_no_bloquea_bajo_el_limite(self, client, user_t1):
        perfil = user_t1.profile
        perfil.investment_total_usd = Decimal('500.00')
        perfil.save()

        client.force_login(user_t1)
        response = client.post('/api/v1/comprar/', data={}, content_type='application/json')
        # No es 403 del middleware (la URL puede no existir aún → 404, o la view responde otra cosa)
        assert response.status_code != 403 or response.json().get('error') != 'limite_kyc_superado'

    def test_no_bloquea_get(self, client, user_t1):
        perfil = user_t1.profile
        perfil.investment_total_usd = Decimal('99999.00')
        perfil.save()

        client.force_login(user_t1)
        response = client.get('/api/v1/comprar/')
        assert response.status_code != 403 or (
            response.headers.get('Content-Type', '').startswith('application/json')
            and response.json().get('error') != 'limite_kyc_superado'
        )

    def test_no_bloquea_t4_bajo_limite_alto(self, client, user_t4):
        perfil = user_t4.profile
        perfil.investment_total_usd = Decimal('50000.00')  # bajo el límite de $100k de T4
        perfil.save()

        client.force_login(user_t4)
        response = client.post('/api/v1/comprar/', data={}, content_type='application/json')
        assert response.status_code != 403 or response.json().get('error') != 'limite_kyc_superado'

    def test_anonimo_no_es_bloqueado_por_middleware(self, client):
        response = client.post('/api/v1/comprar/', data={}, content_type='application/json')
        # Sin usuario, el middleware no aplica (la view exigirá auth por su cuenta)
        assert response.status_code != 403 or response.json().get('error') != 'limite_kyc_superado'
