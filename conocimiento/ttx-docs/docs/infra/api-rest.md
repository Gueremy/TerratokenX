# API REST — TerraTokenX

## Convenciones

- Versionado: `/api/v1/`
- Auth: `Authorization: Bearer <access_token>` en todos los endpoints protegidos
- Paginación: `PageNumberPagination`, 20 items por página
- Errores: siempre JSON `{"error": "codigo", "message": "descripción legible"}`

---

## Endpoints Fase 1 (Semanas 2-6)

### Públicos (sin auth)

```
GET  /api/v1/proyectos/                   → lista marketplace (activos con drop)
GET  /api/v1/proyectos/<slug>/            → detalle proyecto
GET  /api/v1/proyectos/<slug>/drop/       → drop activo actual
GET  /api/v1/tiers/                       → configuración pública de tiers
GET  /api/v1/fees/                        → fee schedule público
```

### Auth

```
POST /api/v1/auth/login/                  → {email, password} → {access, refresh}
POST /api/v1/auth/refresh/                → {refresh} → {access}
POST /api/v1/auth/logout/                 → {refresh} → 205
POST /api/v1/auth/registro/               → crear cuenta
POST /api/v1/auth/password/reset/         → solicitar reset
POST /api/v1/auth/password/reset/confirm/ → confirmar reset
```

### Inversor (auth requerida)

```
GET  /api/v1/mis-inversiones/             → historial de Reservas del usuario
GET  /api/v1/mis-creditos/                → saldo, tier, expiración
GET  /api/v1/mis-creditos/historial/      → CreditTransaction del usuario
POST /api/v1/creditos/comprar/            → iniciar compra de créditos
POST /api/v1/comprar/                     → iniciar compra de tokens (crea Reserva)
GET  /api/v1/perfil/                      → UserProfile del usuario autenticado
PUT  /api/v1/perfil/                      → actualizar datos básicos
POST /api/v1/kyc/iniciar/                 → crear sesión Didit → devuelve session_url
```

### Fraccionador (grupo Fractionalizer)

```
GET  /api/v1/fraccionador/proyectos/      → mis proyectos
POST /api/v1/fraccionador/proyectos/      → crear proyecto
GET  /api/v1/fraccionador/proyectos/<id>/ → detalle mi proyecto
PUT  /api/v1/fraccionador/proyectos/<id>/ → editar mi proyecto
GET  /api/v1/fraccionador/ventas/         → mis reservas confirmadas
GET  /api/v1/fraccionador/drops/          → drops de mis proyectos
POST /api/v1/fraccionador/drops/          → crear drop
```

### Webhooks (sin auth, verificación por firma)

```
POST /api/webhooks/mp/                    → MercadoPago
POST /api/webhooks/cryptomus/             → Cryptomus
POST /api/webhooks/kushki/                → Kushki
POST /api/webhooks/didit/                 → Didit KYC
```

### Admin Joan (superuser o grupo JoanAdmin)

```
GET  /api/v1/admin/proyectos/             → todos los proyectos
PUT  /api/v1/admin/tiers/<id>/            → editar configuración de tier
PUT  /api/v1/admin/fees/<id>/             → editar fee
GET  /api/v1/admin/fraccionadores/        → lista fraccionadores pendientes
POST /api/v1/admin/fraccionadores/<id>/aprobar/  → aprobar fraccionador
POST /api/v1/admin/fraccionadores/<id>/rechazar/ → rechazar
GET  /api/v1/admin/auditlog/              → log de auditoría
```

---

## Serializer pattern

```python
# booking/serializers.py

class ProyectoListSerializer(serializers.ModelSerializer):
    """Ligero — para el marketplace. Solo lo necesario."""
    drop_activo = serializers.SerializerMethodField()
    progreso_pct = serializers.SerializerMethodField()

    def get_drop_activo(self, obj):
        drops = obj.drops.all()  # ya viene en prefetch_related
        activo = next((d for d in drops if d.activo), None)
        if not activo:
            return None
        return {
            'stock': activo.stock_disponible,
            'precio': str(activo.precio_override or obj.precio_token),
            'fecha_fin': activo.fecha_fin.isoformat(),
        }

    def get_progreso_pct(self, obj):
        if obj.tokens_totales == 0:
            return 0
        return round((obj.tokens_vendidos / obj.tokens_totales) * 100, 1)

    class Meta:
        model = Proyecto
        fields = [
            'id', 'nombre', 'slug', 'precio_token',
            'tokens_totales', 'tokens_vendidos', 'progreso_pct',
            'drop_activo', 'owner_type',
        ]


class CompraSerializer(serializers.Serializer):
    """Validación estricta del input de compra."""
    proyecto_id       = serializers.IntegerField(min_value=1)
    cantidad_tokens   = serializers.IntegerField(min_value=1, max_value=10_000)
    metodo_pago       = serializers.ChoiceField(choices=['MP', 'CRYPTO', 'KUSHKI', 'CREDITO'])
    creditos_aplicar  = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        min_value=Decimal('0.00'),
        required=False, default=Decimal('0.00'),
    )
```

---

## Respuestas de error estandarizadas

```python
# booking/utils.py

def error_response(code: str, message: str, status: int = 400) -> Response:
    return Response({'error': code, 'message': message}, status=status)

# Uso:
return error_response('stock_insuficiente', 'Solo quedan 3 tokens disponibles', 409)
return error_response('limite_kyc', 'Completa tu verificación para continuar', 403)
return error_response('drop_inactivo', 'No hay ventana de venta activa', 404)
```
