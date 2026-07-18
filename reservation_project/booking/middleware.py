from decimal import Decimal

from django.http import JsonResponse

from .constants import KYC_LIMITS_USD, TIER_NOMBRES
from .models import UserProfile


class KYCCheckMiddleware:
    """
    Se activa solo en endpoints de checkout (POST).
    Bloquea si el usuario ya alcanzó su límite de inversión acumulada por tier.
    NO bloquea endpoints de lectura (GET).
    """
    ENDPOINTS_PROTEGIDOS = [
        '/api/v1/comprar/',
        '/api/v1/creditos/comprar/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.method == 'POST'
                and any(request.path.startswith(ep) for ep in self.ENDPOINTS_PROTEGIDOS)):

            user = self._resolver_usuario(request)
            if user is not None:
                resultado = self._verificar_limite_kyc(user)
                if resultado is not None:
                    return resultado

        return self.get_response(request)

    @staticmethod
    def _resolver_usuario(request):
        """Usuario por sesión, o por JWT (la auth DRF corre después del middleware)."""
        if request.user.is_authenticated:
            return request.user
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication
            resultado = JWTAuthentication().authenticate(request)
            if resultado is not None:
                return resultado[0]
        except Exception:
            pass
        return None

    def _verificar_limite_kyc(self, user):
        perfil, _ = UserProfile.objects.get_or_create(user=user)

        limite = Decimal(str(KYC_LIMITS_USD.get(perfil.kyc_tier, 1000)))

        if perfil.investment_total_usd >= limite:
            return JsonResponse(
                {
                    'error': 'limite_kyc_superado',
                    'message': (
                        f'Has alcanzado el límite para tu nivel '
                        f'({TIER_NOMBRES.get(perfil.kyc_tier, perfil.kyc_tier)}). '
                        f'Completa la verificación de identidad para subir de nivel.'
                    ),
                    'tier_actual': perfil.kyc_tier,
                    'limite_usd': str(limite),
                    'acumulado_usd': str(perfil.investment_total_usd),
                },
                status=403
            )
        return None
