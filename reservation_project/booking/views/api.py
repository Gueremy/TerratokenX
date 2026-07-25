"""API REST v1 — endpoints para el frontend React (Dev Asociado).

Convenciones (docs/infra/api-rest.md):
- Versionado /api/v1/
- Auth: Bearer <access_token>
- Errores: {'error': codigo, 'message': texto}
"""

import logging

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from booking.exceptions import (
    CreditoInsuficiente,
    DropInactivo,
    IdempotenciaError,
    LimiteKYCSuperado,
    StockInsuficiente,
)
from booking.models import (
    AuditLog,
    CreditBalance,
    CreditTransaction,
    FeeConfig,
    FraccionadorProfile,
    ProjectDrop,
    Proyecto,
    Reserva,
    TierConfig,
    UserProfile,
)
from booking.permissions import EsDuenioDelProyecto, IsFraccionador, IsJoanAdmin
from booking.selectors import get_drop_activo, get_fee_config_all, get_tier_config_all
from booking.serializers import (
    AuditLogSerializer,
    CompraCreditosSerializer,
    CompraSerializer,
    CreditBalanceSerializer,
    CreditTransactionSerializer,
    DropFraccionadorSerializer,
    DropPublicoSerializer,
    FraccionadorProfileSerializer,
    FraccionadorProyectoSerializer,
    PerfilSerializer,
    ProyectoDetailSerializer,
    ProyectoListSerializer,
    RegistroSerializer,
    ReservaSerializer,
)
from booking.utils import error_response

logger = logging.getLogger('booking')


# ═══════════════════════════════ PÚBLICOS ═══════════════════════════════════

class ProyectosListView(generics.ListAPIView):
    """GET /api/v1/proyectos/ — marketplace público."""
    permission_classes = [AllowAny]
    serializer_class = ProyectoListSerializer

    def get_queryset(self):
        return Proyecto.objects.filter(activo=True).prefetch_related('drops')


class ProyectoDetailView(generics.RetrieveAPIView):
    """GET /api/v1/proyectos/<slug>/"""
    permission_classes = [AllowAny]
    serializer_class = ProyectoDetailSerializer
    lookup_field = 'slug'
    queryset = Proyecto.objects.filter(activo=True).prefetch_related('drops')


class ProyectoDropView(APIView):
    """GET /api/v1/proyectos/<slug>/drop/ — drop activo actual."""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        proyecto = Proyecto.objects.filter(slug=slug, activo=True).first()
        if not proyecto:
            return error_response('proyecto_no_encontrado', 'El proyecto no existe', 404)
        drop = get_drop_activo(proyecto.id)
        if not drop:
            return error_response('drop_inactivo', 'No hay ventana de venta activa', 404)
        return Response(DropPublicoSerializer(drop).data)


class TiersPublicView(APIView):
    """GET /api/v1/tiers/ — configuración pública de tiers (cacheada)."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(get_tier_config_all())


class FeesPublicView(APIView):
    """GET /api/v1/fees/ — fee schedule público (cacheado)."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(get_fee_config_all())


# ═══════════════════════════════ AUTH ═══════════════════════════════════════

class LoginThrottle(AnonRateThrottle):
    scope = 'login'


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — {username|email, password} → {access, refresh}."""
    throttle_classes = [LoginThrottle]


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — blacklistea el refresh token."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return error_response('refresh_requerido', 'refresh token requerido', 400)
        try:
            RefreshToken(refresh_token).blacklist()
            return Response(status=205)
        except TokenError:
            return error_response('token_invalido', 'token inválido', 400)


class RegistroView(APIView):
    """POST /api/v1/auth/registro/ — crear cuenta de inversor."""
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {'access': str(refresh.access_token), 'refresh': str(refresh)},
            status=201,
        )


class PasswordResetView(APIView):
    """POST /api/v1/auth/password/reset/ — envía email con link de reset."""
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return error_response('email_requerido', 'email requerido', 400)

        user = User.objects.filter(email__iexact=email).first()
        if user:
            from django.conf import settings

            from booking.integrations.resend import enviar_recuperacion_password

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_URL}/password-reset/{uid}/{token}/"
            enviar_recuperacion_password(user, reset_url)

        # Siempre 200 — no revelar si el email existe
        return Response({'ok': True})


class PasswordResetConfirmView(APIView):
    """POST /api/v1/auth/password/reset/confirm/ — {uid, token, password}."""
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        uid = request.data.get('uid', '')
        token = request.data.get('token', '')
        password = request.data.get('password', '')

        if len(password) < 8:
            return error_response('password_corta', 'La contraseña debe tener al menos 8 caracteres', 400)

        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return error_response('token_invalido', 'El enlace no es válido', 400)

        if not default_token_generator.check_token(user, token):
            return error_response('token_invalido', 'El enlace expiró o no es válido', 400)

        user.set_password(password)
        user.save(update_fields=['password'])
        return Response({'ok': True})


# ═══════════════════════════════ INVERSOR ═══════════════════════════════════

class MisInversionesView(generics.ListAPIView):
    """GET /api/v1/mis-inversiones/"""
    permission_classes = [IsAuthenticated]
    serializer_class = ReservaSerializer

    def get_queryset(self):
        # SIEMPRE filtrar por usuario — nunca .all()
        return Reserva.objects.filter(user=self.request.user).select_related(
            'proyecto').order_by('-created_at')


class MisCreditosView(APIView):
    """GET /api/v1/mis-creditos/ — saldo, tier, expiración."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        balance = CreditBalance.objects.filter(user=request.user).first()
        if not balance:
            return Response({'balance_usd': '0.00', 'tier': request.user.profile.kyc_tier,
                             'expires_at': None, 'extended': False})
        return Response(CreditBalanceSerializer(balance).data)


class MisCreditosHistorialView(generics.ListAPIView):
    """GET /api/v1/mis-creditos/historial/"""
    permission_classes = [IsAuthenticated]
    serializer_class = CreditTransactionSerializer

    def get_queryset(self):
        return CreditTransaction.objects.filter(user=self.request.user)


class ComprarCreditosView(APIView):
    """POST /api/v1/creditos/comprar/ — inicia compra de créditos."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'checkout'

    def post(self, request):
        serializer = CompraCreditosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from booking.services_creditos import comprar_creditos
        try:
            resultado = comprar_creditos(
                request.user,
                serializer.validated_data['monto_usd'],
                serializer.validated_data['metodo_pago'],
            )
        except LimiteKYCSuperado as e:
            return error_response('limite_creditos', str(e), 403)

        return Response({
            'monto_creditos': str(resultado['monto_creditos']),
            'precio_a_pagar': str(resultado['precio_a_pagar']),
            'descuento_aplicado': str(resultado['descuento_aplicado']),
            'tier': resultado['tier'],
        })


class ComprarView(APIView):
    """POST /api/v1/comprar/ — crea la Reserva PENDIENTE y devuelve datos de pago."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'checkout'

    def post(self, request):
        serializer = CompraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        from booking.services import crear_reserva_pendiente
        try:
            reserva = crear_reserva_pendiente(
                proyecto_id=datos['proyecto_id'],
                user=request.user,
                cantidad_tokens=datos['cantidad_tokens'],
                metodo_pago=datos['metodo_pago'],
                creditos_aplicar=datos['creditos_aplicar'],
            )
        except DropInactivo as e:
            return error_response('drop_inactivo', str(e), 404)
        except StockInsuficiente as e:
            return error_response('stock_insuficiente', str(e), 409)
        except LimiteKYCSuperado as e:
            return error_response('limite_kyc', str(e), 403)
        except CreditoInsuficiente as e:
            return error_response('credito_insuficiente', str(e), 400)

        respuesta = {'reserva': ReservaSerializer(reserva).data}

        # Generar los datos de pago según el método
        try:
            if datos['metodo_pago'] == 'CRYPTO':
                from booking.integrations.cryptomus import crear_invoice
                invoice = crear_invoice(str(reserva.total), str(reserva.id))
                reserva.cryptomus_uuid = invoice.get('uuid')
                reserva.save(update_fields=['cryptomus_uuid'])
                respuesta['pago'] = {'metodo': 'CRYPTO', 'url': invoice.get('url')}
            elif datos['metodo_pago'] == 'KUSHKI':
                if not datos.get('kushki_token'):
                    return error_response('kushki_token_requerido', 'Falta el token de tarjeta', 400)
                from booking.integrations.kushki import cobrar_con_token
                reserva.kushki_token = datos['kushki_token']
                reserva.save(update_fields=['kushki_token'])
                cobro = cobrar_con_token(datos['kushki_token'], str(reserva.total), reserva.id)
                respuesta['pago'] = {'metodo': 'KUSHKI', 'resultado': cobro}
            elif datos['metodo_pago'] == 'MP':
                respuesta['pago'] = {
                    'metodo': 'MP',
                    'detalle': 'Usar create-preference con el id de la reserva',
                    'preference_endpoint': f'/create-preference/{reserva.id}/',
                }
            elif datos['metodo_pago'] == 'CREDITO':
                # Pago 100% con créditos: si el total quedó en 0, confirmar de inmediato
                if reserva.total == 0:
                    from booking.services import confirmar_reserva
                    try:
                        reserva = confirmar_reserva(reserva.id)
                    except IdempotenciaError:
                        pass
                    respuesta['reserva'] = ReservaSerializer(reserva).data
                respuesta['pago'] = {'metodo': 'CREDITO', 'estado': reserva.estado_pago}
        except Exception as e:
            logger.error("Error generando pago para reserva %s: %s", reserva.id, e)
            respuesta['pago'] = {'error': 'pago_no_generado',
                                 'message': 'La reserva quedó pendiente; reintenta el pago'}

        return Response(respuesta, status=201)


class PerfilView(APIView):
    """GET/PUT /api/v1/perfil/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        perfil, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(PerfilSerializer(perfil).data)

    def put(self, request):
        perfil, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = PerfilSerializer(perfil, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class KYCIniciarView(APIView):
    """POST /api/v1/kyc/iniciar/ — crea sesión Didit y devuelve session_url."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tier_requerido = int(request.data.get('tier_requerido', 2))
        if tier_requerido not in (2, 3):
            return error_response(
                'tier_invalido',
                'La verificación automática cubre T2 y T3. T4 Black requiere revisión manual.',
                400,
            )

        from booking.integrations.didit import iniciar_sesion_kyc
        try:
            resultado = iniciar_sesion_kyc(request.user.id, tier_requerido)
        except Exception as e:
            logger.error("Error creando sesión Didit para user %s: %s", request.user.id, e)
            return error_response('kyc_no_disponible', 'No se pudo iniciar la verificación', 502)

        UserProfile.objects.filter(user=request.user).update(
            didit_session_id=resultado['session_id']
        )
        return Response({'session_url': resultado['session_url']})


# ═══════════════════════════════ FRACCIONADOR ════════════════════════════════

class FraccionadorProyectosView(generics.ListCreateAPIView):
    """GET/POST /api/v1/fraccionador/proyectos/"""
    permission_classes = [IsAuthenticated, IsFraccionador]
    serializer_class = FraccionadorProyectoSerializer

    def get_queryset(self):
        return Proyecto.objects.filter(owner=self.request.user)


class FraccionadorProyectoDetailView(generics.RetrieveUpdateAPIView):
    """GET/PUT /api/v1/fraccionador/proyectos/<id>/"""
    permission_classes = [IsAuthenticated, IsFraccionador, EsDuenioDelProyecto]
    serializer_class = FraccionadorProyectoSerializer

    def get_queryset(self):
        return Proyecto.objects.filter(owner=self.request.user)


class FraccionadorVentasView(generics.ListAPIView):
    """GET /api/v1/fraccionador/ventas/ — reservas confirmadas de mis proyectos."""
    permission_classes = [IsAuthenticated, IsFraccionador]
    serializer_class = ReservaSerializer

    def get_queryset(self):
        return Reserva.objects.filter(
            proyecto__owner=self.request.user,
            estado_pago='CONFIRMADO',
        ).select_related('proyecto').order_by('-created_at')


class FraccionadorDropsView(generics.ListCreateAPIView):
    """GET/POST /api/v1/fraccionador/drops/"""
    permission_classes = [IsAuthenticated, IsFraccionador]
    serializer_class = DropFraccionadorSerializer

    def get_queryset(self):
        return ProjectDrop.objects.filter(
            proyecto__owner=self.request.user).order_by('proyecto', 'numero')


# ═══════════════════════════════ ADMIN JOAN ══════════════════════════════════

class AdminProyectosView(generics.ListAPIView):
    """GET /api/v1/admin/proyectos/ — todos los proyectos."""
    permission_classes = [IsAuthenticated, IsJoanAdmin]
    serializer_class = ProyectoListSerializer
    queryset = Proyecto.objects.all().prefetch_related('drops')


class _AuditaCambiosMixin:
    """Registra en AuditLog cualquier cambio a la configuración de dinero."""
    accion_auditoria = 'config.modificada'

    def perform_update(self, serializer):
        antes = {
            campo: str(valor)
            for campo, valor in serializer.instance.__dict__.items()
            if not campo.startswith('_')
        }
        instancia = serializer.save()
        despues = {
            campo: str(valor)
            for campo, valor in instancia.__dict__.items()
            if not campo.startswith('_')
        }
        AuditLog.registrar(
            accion=self.accion_auditoria,
            objeto=instancia,
            user=self.request.user,
            datos_antes=antes,
            datos_despues=despues,
            request=self.request,
        )


class AdminTierUpdateView(_AuditaCambiosMixin, generics.UpdateAPIView):
    """PUT /api/v1/admin/tiers/<id>/"""
    permission_classes = [IsAuthenticated, IsJoanAdmin]
    queryset = TierConfig.objects.all()
    accion_auditoria = 'tier.modificado'

    def get_serializer_class(self):
        from booking.serializers import TierConfigAdminSerializer
        return TierConfigAdminSerializer


class AdminFeeUpdateView(_AuditaCambiosMixin, generics.UpdateAPIView):
    """PUT /api/v1/admin/fees/<id>/"""
    permission_classes = [IsAuthenticated, IsJoanAdmin]
    queryset = FeeConfig.objects.all()
    accion_auditoria = 'fee.modificado'

    def get_serializer_class(self):
        from booking.serializers import FeeConfigAdminSerializer
        return FeeConfigAdminSerializer


class AdminFraccionadoresView(generics.ListAPIView):
    """GET /api/v1/admin/fraccionadores/ — pendientes primero."""
    permission_classes = [IsAuthenticated, IsJoanAdmin]
    serializer_class = FraccionadorProfileSerializer

    def get_queryset(self):
        qs = FraccionadorProfile.objects.select_related('user')
        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(kyb_estado=estado)
        return qs.order_by('kyb_estado')


class AdminFraccionadorAccionView(APIView):
    """POST /api/v1/admin/fraccionadores/<id>/aprobar|rechazar/"""
    permission_classes = [IsAuthenticated, IsJoanAdmin]

    def post(self, request, pk, accion):
        from django.utils import timezone

        perfil = FraccionadorProfile.objects.filter(pk=pk).first()
        if not perfil:
            return error_response('no_encontrado', 'Fraccionador no encontrado', 404)

        if accion == 'aprobar':
            perfil.kyb_estado = 'APROBADO'
            perfil.kyb_fecha_aprobacion = timezone.now()
            # Agregar al grupo Fractionalizer
            from django.contrib.auth.models import Group
            grupo, _ = Group.objects.get_or_create(name='Fractionalizer')
            perfil.user.groups.add(grupo)
        elif accion == 'rechazar':
            perfil.kyb_estado = 'RECHAZADO'
        else:
            return error_response('accion_invalida', 'Acción debe ser aprobar o rechazar', 400)

        perfil.kyb_revisado_por = request.user
        perfil.kyb_notas = request.data.get('notas', perfil.kyb_notas)
        perfil.save()

        AuditLog.registrar(
            accion=f'fraccionador.{accion}',
            objeto=perfil,
            user=request.user,
            request=request,
        )
        return Response(FraccionadorProfileSerializer(perfil).data)


class AdminAuditLogView(generics.ListAPIView):
    """GET /api/v1/admin/auditlog/"""
    permission_classes = [IsAuthenticated, IsJoanAdmin]
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user')
        accion = self.request.query_params.get('accion')
        if accion:
            qs = qs.filter(accion=accion)
        return qs
