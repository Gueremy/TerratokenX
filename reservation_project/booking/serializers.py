from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
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


# ── Proyectos / Marketplace ──────────────────────────────────────────────────

class DropPublicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDrop
        fields = ['id', 'nombre', 'numero', 'stock_disponible', 'precio_override',
                  'fecha_inicio', 'fecha_fin', 'activo']


class ProyectoListSerializer(serializers.ModelSerializer):
    """Ligero — para el marketplace. Solo lo necesario."""
    drop_activo = serializers.SerializerMethodField()
    progreso_pct = serializers.SerializerMethodField()

    class Meta:
        model = Proyecto
        fields = [
            'id', 'nombre', 'slug', 'ubicacion', 'precio_token',
            'tokens_totales', 'tokens_vendidos', 'progreso_pct',
            'drop_activo', 'owner_type', 'tipo', 'estado',
            'imagen_portada_url',
        ]

    def get_drop_activo(self, obj):
        from django.utils import timezone
        ahora = timezone.now()
        activo = next(
            (d for d in obj.drops.all()
             if d.activo and d.fecha_inicio <= ahora <= d.fecha_fin and d.stock_disponible > 0),
            None,
        )
        if not activo:
            return None
        return {
            'stock': activo.stock_disponible,
            'precio': str(activo.precio_override or obj.precio_token),
            'fecha_fin': activo.fecha_fin.isoformat(),
        }

    def get_progreso_pct(self, obj):
        if not obj.tokens_totales:
            return 0
        return round((obj.tokens_vendidos / obj.tokens_totales) * 100, 1)


class ProyectoDetailSerializer(ProyectoListSerializer):
    drops = DropPublicoSerializer(many=True, read_only=True)

    class Meta(ProyectoListSerializer.Meta):
        fields = ProyectoListSerializer.Meta.fields + [
            'descripcion', 'video_url', 'pagina_oficial_url', 'gps_data', 'drops',
        ]


# ── Compras ──────────────────────────────────────────────────────────────────

class CompraSerializer(serializers.Serializer):
    """Validación estricta del input de compra."""
    proyecto_id = serializers.IntegerField(min_value=1)
    cantidad_tokens = serializers.IntegerField(min_value=1, max_value=10_000)
    metodo_pago = serializers.ChoiceField(choices=['MP', 'CRYPTO', 'KUSHKI', 'CREDITO'])
    creditos_aplicar = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        min_value=Decimal('0.00'),
        required=False, default=Decimal('0.00'),
    )
    kushki_token = serializers.CharField(required=False, allow_blank=True, max_length=100)


class CompraCreditosSerializer(serializers.Serializer):
    monto_usd = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('1.00'))
    metodo_pago = serializers.ChoiceField(choices=['MP', 'CRYPTO', 'KUSHKI'])


class GPSDataSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    zoom = serializers.IntegerField(min_value=1, max_value=20, required=False)


# ── Inversor ─────────────────────────────────────────────────────────────────

class ReservaSerializer(serializers.ModelSerializer):
    proyecto_nombre = serializers.CharField(source='proyecto.nombre', read_only=True, default=None)
    proyecto_slug = serializers.CharField(source='proyecto.slug', read_only=True, default=None)

    class Meta:
        model = Reserva
        fields = [
            'id', 'numero_reserva', 'proyecto_nombre', 'proyecto_slug',
            'cantidad_tokens', 'total', 'estado_pago', 'metodo_pago',
            'created_at', 'tx_hash',
        ]


class CreditBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditBalance
        fields = ['balance_usd', 'tier', 'expires_at', 'extended']


class CreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditTransaction
        fields = ['id', 'tipo', 'monto_usd', 'reserva', 'descripcion', 'created_at']


class PerfilSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)

    class Meta:
        model = UserProfile
        fields = [
            'email', 'first_name', 'last_name', 'rut', 'telefono', 'direccion',
            'kyc_status', 'kyc_tier', 'investment_total_usd',
            'kyc_verificado_en', 'wallet_address',
        ]
        read_only_fields = ['kyc_status', 'kyc_tier', 'investment_total_usd', 'kyc_verificado_en']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()
        return super().update(instance, validated_data)


class RegistroSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este email.')
        return value

    def create(self, validated_data):
        email = validated_data['email']
        username = email.split('@')[0]
        base = username
        contador = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{contador}"
            contador += 1
        return User.objects.create_user(
            username=username,
            email=email,
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )


# ── Configuración pública ────────────────────────────────────────────────────

class TierConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TierConfig
        fields = ['tier', 'nombre', 'cap_creditos_usd', 'descuento_fees_pct',
                  'descuento_creditos_pct', 'kyc_requerido']


class FeeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeConfig
        fields = ['tipo', 'porcentaje', 'monto_minimo_usd', 'descripcion', 'activo']


# ── Fraccionador ─────────────────────────────────────────────────────────────

class FraccionadorProyectoSerializer(serializers.ModelSerializer):
    gps_data = GPSDataSerializer(required=False, allow_null=True)

    class Meta:
        model = Proyecto
        fields = [
            'id', 'nombre', 'slug', 'descripcion', 'ubicacion', 'precio_token',
            'tokens_totales', 'tokens_vendidos', 'tipo', 'estado', 'activo',
            'gps_data', 'spv_legal_name', 'venta_solo_drops',
            'imagen_portada_url', 'video_url',
        ]
        read_only_fields = ['slug', 'tokens_vendidos']

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        validated_data['owner_type'] = 'EXTERNAL'
        return super().create(validated_data)


class DropFraccionadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDrop
        fields = ['id', 'proyecto', 'nombre', 'numero', 'stock_total',
                  'stock_disponible', 'precio_override', 'fecha_inicio',
                  'fecha_fin', 'activo']

    def validate(self, attrs):
        proyecto = attrs.get('proyecto')
        request = self.context.get('request')
        if proyecto and request and proyecto.owner != request.user:
            raise serializers.ValidationError('El proyecto no te pertenece.')
        return attrs


class FraccionadorProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = FraccionadorProfile
        fields = ['id', 'email', 'kyb_estado', 'tipo', 'razon_social', 'rut_empresa',
                  'tokens_reserve_pct', 'kyb_fecha_aprobacion', 'kyb_notas']
        read_only_fields = ['kyb_estado', 'kyb_fecha_aprobacion', 'kyb_notas']


# ── Admin ────────────────────────────────────────────────────────────────────

class TierConfigAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = TierConfig
        fields = ['id', 'tier', 'nombre', 'cap_creditos_usd', 'descuento_fees_pct',
                  'descuento_creditos_pct', 'kyc_requerido']
        read_only_fields = ['tier']


class FeeConfigAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeConfig
        fields = ['id', 'tipo', 'porcentaje', 'monto_minimo_usd', 'descripcion', 'activo']
        read_only_fields = ['tipo']


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = ['id', 'accion', 'objeto_tipo', 'objeto_id', 'user_email',
                  'datos_antes', 'datos_despues', 'ip_address', 'created_at']
