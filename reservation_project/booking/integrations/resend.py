"""Email transaccional vía Resend (reemplaza SendGrid).

Free tier: 3.000 emails/mes. En local (sin RESEND_API_KEY) imprime a consola
mediante el backend de email de Django.
"""

import logging

from django.conf import settings

logger = logging.getLogger('booking.email')


def _enviar(to: str, subject: str, html: str) -> bool:
    """Función base. Todos los emails pasan por aquí."""
    try:
        if settings.RESEND_API_KEY:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                'from': settings.EMAIL_FROM,
                'to': [to],
                'subject': subject,
                'html': html,
            })
        else:
            # Sin API key (desarrollo local): usar backend de Django (consola)
            from django.core.mail import send_mail
            send_mail(subject, '', settings.EMAIL_FROM, [to], html_message=html)

        logger.info('email.enviado', extra={'to': to, 'subject': subject})
        return True
    except Exception as e:
        logger.error('email.error', extra={'to': to, 'error': str(e)})
        return False


# ─── Templates de email ──────────────────────────────────────────────────────

def enviar_confirmacion_reserva(reserva) -> bool:
    html = f"""
    <h2>¡Tu compra fue confirmada!</h2>
    <p>Hola {reserva.user.first_name or reserva.correo if reserva.user else reserva.nombre},</p>
    <p>Tu compra de <strong>{reserva.cantidad_tokens} tokens</strong>
       del proyecto <strong>{reserva.proyecto.nombre if reserva.proyecto else 'TerraTokenX'}</strong> fue procesada.</p>
    <p>Total pagado: <strong>${reserva.total} USD</strong></p>
    <p>Puedes ver tu portafolio en tu panel de inversor.</p>
    <hr>
    <small>TerraTokenX · Los créditos no representan garantía financiera.</small>
    """
    return _enviar(
        to=reserva.correo,
        subject=f'Compra confirmada — {reserva.proyecto.nombre if reserva.proyecto else "TerraTokenX"}',
        html=html,
    )


def enviar_kyc_aprobado(user) -> bool:
    from booking.constants import TIER_NOMBRES

    tier = user.profile.kyc_tier
    html = f"""
    <h2>Verificación completada</h2>
    <p>Hola {user.first_name or user.email},</p>
    <p>Tu identidad fue verificada. Ahora tienes acceso al nivel
       <strong>{TIER_NOMBRES.get(tier, tier)}</strong>.</p>
    <p>Esto te permite acceder a proyectos y créditos con mayores límites.</p>
    """
    return _enviar(
        to=user.email,
        subject='Tu identidad fue verificada — TerraTokenX',
        html=html,
    )


def enviar_drop_activo(user, proyecto) -> bool:
    html = f"""
    <h2>Ventana de compra abierta</h2>
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


def enviar_alerta_admin(asunto: str, mensaje: str) -> bool:
    """Alerta interna para Joan/admin."""
    html = f"<h3>{asunto}</h3><p>{mensaje}</p>"
    return _enviar(
        to=settings.EMAIL_FROM,
        subject=f'[TerraTokenX Admin] {asunto}',
        html=html,
    )
