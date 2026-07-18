from django.db import models


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class AuditLog(models.Model):
    """Inmutable: no hay update ni delete. Registro de todo lo importante."""
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    accion = models.CharField(max_length=100)     # 'reserva.confirmada', 'kyc.aprobado'
    objeto_tipo = models.CharField(max_length=50)  # 'Reserva', 'UserProfile'
    objeto_id = models.IntegerField(null=True)
    datos_antes = models.JSONField(null=True)
    datos_despues = models.JSONField(null=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['accion', 'created_at']),
            models.Index(fields=['objeto_tipo', 'objeto_id']),
        ]

    def __str__(self):
        return f"{self.accion} ({self.objeto_tipo} #{self.objeto_id})"

    @classmethod
    def registrar(cls, accion: str, objeto=None, user=None,
                  datos_antes=None, datos_despues=None, request=None):
        """Factory method para crear logs sin boilerplate."""
        return cls.objects.create(
            accion=accion,
            user=user or (request.user if request and request.user.is_authenticated else None),
            objeto_tipo=type(objeto).__name__ if objeto else '',
            objeto_id=objeto.pk if objeto else None,
            datos_antes=datos_antes,
            datos_despues=datos_despues,
            ip_address=_get_client_ip(request) if request else None,
            user_agent=(request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''),
        )
