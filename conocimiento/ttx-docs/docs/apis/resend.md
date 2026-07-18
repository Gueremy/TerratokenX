# Resend — Email Transaccional

**Qué hace:** Envía todos los emails transaccionales de la plataforma.
**Por qué Resend:** SendGrid eliminó su free tier en mayo 2025. Resend da 3.000 emails/mes gratis permanente.
**Docs:** https://resend.com/docs

---

## ⚙️ CREDENCIALES REQUERIDAS

```
Antes de implementar esta sección, decirle a Gueremy:
"Necesito las credenciales de Resend para continuar."

□ RESEND_API_KEY
  → Obtener en: https://resend.com → Sign Up (gratis) → API Keys → Create API Key
  → Copiar el valor que empieza con "re_"

□ EMAIL_FROM
  → El email remitente: noreply@terratokenx.com
  → Requiere verificar el dominio en Resend (agregar DNS records)
  → En local, para tests: se puede usar onboarding@resend.dev (no requiere verificación)

Free tier: 3.000 emails/mes, 100/día. Sin tarjeta de crédito.
Tiempo de setup: 15 minutos (incluye verificación de dominio).
```

---

## Configuración Django

```python
# settings/base.py
RESEND_API_KEY = config('RESEND_API_KEY')
EMAIL_FROM = config('EMAIL_FROM', default='noreply@terratokenx.com')

# settings/local.py
# En desarrollo, imprimir en consola para no gastar el free tier
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

---

## Integración

```python
# booking/integrations/resend.py
import resend   # pip install resend
import logging
from django.conf import settings

logger = logging.getLogger('booking.email')

resend.api_key = settings.RESEND_API_KEY


def _enviar(to: str, subject: str, html: str) -> bool:
    """Función base. Todos los emails pasan por aquí."""
    try:
        params = {
            'from': settings.EMAIL_FROM,
            'to': [to],
            'subject': subject,
            'html': html,
        }
        resend.Emails.send(params)
        logger.info('email.enviado', extra={'to': to, 'subject': subject})
        return True
    except Exception as e:
        logger.error('email.error', extra={'to': to, 'error': str(e)})
        return False


# ─── Templates de email ──────────────────────────────────────────────────────

def enviar_confirmacion_reserva(reserva) -> bool:
    html = f"""
    <h2>¡Tu compra fue confirmada!</h2>
    <p>Hola {reserva.user.first_name or reserva.user.email},</p>
    <p>Tu compra de <strong>{reserva.cantidad_tokens} tokens</strong>
       del proyecto <strong>{reserva.proyecto.nombre}</strong> fue procesada.</p>
    <p>Total pagado: <strong>${reserva.total} USD</strong></p>
    <p>Puedes ver tu portafolio en tu panel de inversor.</p>
    <hr>
    <small>TerraTokenX · Los créditos no representan garantía de retorno.</small>
    """
    return _enviar(
        to=reserva.user.email,
        subject=f'Compra confirmada — {reserva.proyecto.nombre}',
        html=html,
    )


def enviar_kyc_aprobado(user) -> bool:
    from .constants import TIER_NOMBRES
    tier = user.userprofile.kyc_tier
    html = f"""
    <h2>Verificación completada</h2>
    <p>Hola {user.first_name or user.email},</p>
    <p>Tu identidad fue verificada. Ahora tienes acceso al nivel
       <strong>{TIER_NOMBRES[tier]}</strong>.</p>
    <p>Esto te permite acceder a proyectos y créditos con mayores límites.</p>
    """
    return _enviar(
        to=user.email,
        subject='Tu identidad fue verificada — TerraTokenX',
        html=html,
    )


def enviar_drop_activo(user, proyecto) -> bool:
    html = f"""
    <h2>⚡ Ventana de compra abierta</h2>
    <p>Hola {user.first_name or user.email},</p>
    <p>Hay una nueva ventana de acceso disponible para
       <strong>{proyecto.nombre}</strong>.</p>
    <p>Las ventanas son limitadas — el stock disponible se agota.</p>
    <p><a href="{settings.FRONTEND_URL}/proyectos/{proyecto.slug}/">Ver proyecto</a></p>
    """
    return _enviar(
        to=user.email,
        subject=f'Nueva ventana disponible — {proyecto.nombre}',
        html=html,
    )


def enviar_recuperacion_password(user, reset_url: str) -> bool:
    html = f"""
    <h2>Recuperar contraseña</h2>
    <p>Hola {user.first_name or user.email},</p>
    <p>Recibimos una solicitud para restablecer tu contraseña.</p>
    <p><a href="{reset_url}">Haz click aquí para restablecer tu contraseña</a></p>
    <p>Si no solicitaste esto, ignora este email. El enlace vence en 1 hora.</p>
    """
    return _enviar(
        to=user.email,
        subject='Restablecer contraseña — TerraTokenX',
        html=html,
    )


def enviar_creditos_por_vencer(user, balance) -> bool:
    html = f"""
    <h2>Tus créditos vencen pronto</h2>
    <p>Hola {user.first_name or user.email},</p>
    <p>Tienes <strong>${balance.balance_usd} USD en créditos</strong>
       que vencen el <strong>{balance.expires_at.strftime('%d/%m/%Y')}</strong>.</p>
    <p>Úsalos antes de esa fecha en cualquier proyecto disponible.</p>
    """
    return _enviar(
        to=user.email,
        subject='Tus créditos vencen pronto — TerraTokenX',
        html=html,
    )
```

---

## Lista completa de emails del sistema

| Email | Cuándo se envía | Función |
|-------|----------------|---------|
| Confirmación de reserva | Pago confirmado | `enviar_confirmacion_reserva` |
| KYC aprobado | Webhook Didit approved | `enviar_kyc_aprobado` |
| Drop activo | Joan activa un Drop | `enviar_drop_activo` |
| Recuperación de contraseña | Solicitud de reset | `enviar_recuperacion_password` |
| Créditos por vencer | 7 días antes de expirar | `enviar_creditos_por_vencer` |
| Retiro aprobado (fraccionador) | Joan aprueba retiro | `enviar_retiro_aprobado` (v2) |
| KYB aprobado (fraccionador) | Joan aprueba KYB | `enviar_kyb_aprobado` (v2) |

---

## Tests

```python
def test_email_confirmacion_se_llama_al_confirmar(mock_resend, reserva_pendiente):
    """El email de confirmación se envía cuando se confirma la reserva."""
    confirmar_reserva(reserva_pendiente.id)
    mock_resend.assert_called_once()
    call_args = mock_resend.call_args[0][0]
    assert reserva_pendiente.user.email in call_args['to']
    assert 'confirmada' in call_args['subject'].lower()
```
