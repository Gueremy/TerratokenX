# Auth y Autorización — TerraTokenX

## Stack de auth

- **JWT** con `djangorestframework-simplejwt`
- **Blacklist** de tokens al logout (evita tokens activos después de cerrar sesión)
- **Rate limiting** en endpoints sensibles
- **Permission classes** por rol

---

## Endpoints de autenticación

```python
# booking/urls.py
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('api/v1/auth/login/',    LoginView.as_view(),       name='auth-login'),
    path('api/v1/auth/refresh/',  TokenRefreshView.as_view(), name='token-refresh'),
    path('api/v1/auth/logout/',   LogoutView.as_view(),       name='auth-logout'),
    path('api/v1/auth/registro/', RegistroView.as_view(),     name='auth-registro'),
    path('api/v1/auth/password/reset/', PasswordResetView.as_view(), name='password-reset'),
    path('api/v1/auth/password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
```

---

## Login view con rate limiting

```python
# booking/views/api.py
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView


class LoginThrottle(AnonRateThrottle):
    rate = '10/hour'    # max 10 intentos de login por hora por IP
    scope = 'login'


class LoginView(TokenObtainPairView):
    throttle_classes = [LoginThrottle]
```

---

## Logout con blacklist

```python
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'refresh token requerido'}, status=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=205)
        except TokenError:
            return Response({'error': 'token inválido'}, status=400)
```

---

## Permission classes

```python
# booking/permissions.py
from rest_framework.permissions import BasePermission


class IsFraccionador(BasePermission):
    """Solo usuarios del grupo Fractionalizer."""
    message = 'Se requiere cuenta de fraccionador verificada.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.groups.filter(name='Fractionalizer').exists()
        )


class EsDuenioDelProyecto(BasePermission):
    """A nivel de objeto: solo el dueño puede ver/editar su proyecto."""
    message = 'No tienes permiso para acceder a este proyecto.'

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsJoanAdmin(BasePermission):
    """Solo Joan (superuser o grupo JoanAdmin)."""
    message = 'Acceso restringido al administrador.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.groups.filter(name='JoanAdmin').exists()
            )
        )
```

---

## Uso en views

```python
class MisProyectosView(ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsFraccionador]
    serializer_class = ProyectoListSerializer

    def get_queryset(self):
        # SIEMPRE filtrar por usuario — nunca .all()
        return Proyecto.objects.filter(owner=self.request.user)


class ProyectoDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsFraccionador, EsDuenioDelProyecto]
    serializer_class = ProyectoDetailSerializer

    def get_queryset(self):
        return Proyecto.objects.filter(owner=self.request.user)
```

---

## Grupos en DB — crear en Bloque 0

```python
# Script para crear grupos (correr en manage.py shell o migration)
from django.contrib.auth.models import Group

Group.objects.get_or_create(name='Fractionalizer')
Group.objects.get_or_create(name='JoanAdmin')
```

O crear via migración de datos:

```python
# booking/migrations/XXXX_crear_grupos.py
from django.db import migrations


def crear_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='Fractionalizer')
    Group.objects.get_or_create(name='JoanAdmin')


class Migration(migrations.Migration):
    dependencies = [('booking', 'XXXX_migracion_anterior')]

    operations = [
        migrations.RunPython(crear_grupos, migrations.RunPython.noop),
    ]
```

---

## Configuración completa de JWT

```python
# settings/base.py
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':  True,   # cada refresh genera nuevo refresh token
    'BLACKLIST_AFTER_ROTATION': True, # el viejo queda inválido inmediatamente
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}
```

---

## Web3 Login (Fase 3 — NO implementar hasta semana 13)

Ver `docs/blockchain.md §web3-login` cuando llegue la semana 13.
Resumen: el usuario firma un nonce con Metamask → Django verifica con web3.py → genera JWT normal.
No requiere cambios en el sistema de JWT actual.
