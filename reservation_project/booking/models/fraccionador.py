from decimal import Decimal

from django.db import models

from .. import validators


class FraccionadorProfile(models.Model):
    """Perfil KYB del fraccionador. Los retiros/distribuciones son de Fase 2 (DIFERIDO)."""
    KYB_ESTADOS = [
        ('PENDIENTE', 'Pendiente revisión'),
        ('EN_REVISION', 'En revisión'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('MAS_DOCS', 'Requiere más documentos'),
    ]
    TIPOS = [('PERSONA', 'Persona natural'), ('EMPRESA', 'Empresa')]

    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='fraccionador_profile')
    kyb_estado = models.CharField(max_length=20, choices=KYB_ESTADOS, default='PENDIENTE')
    tipo = models.CharField(max_length=10, choices=TIPOS, default='PERSONA')
    razon_social = models.CharField(max_length=200, blank=True)
    rut_empresa = models.CharField(max_length=12, blank=True)

    # Documentos
    doc_dominio_vigente = models.FileField(upload_to=validators.ruta_kyb_dominios, null=True, blank=True, validators=[validators.validar_archivo_kyc])
    doc_escritura = models.FileField(upload_to=validators.ruta_kyb_escrituras, null=True, blank=True, validators=[validators.validar_archivo_kyc])
    doc_tasacion = models.FileField(upload_to=validators.ruta_kyb_tasaciones, null=True, blank=True, validators=[validators.validar_archivo_kyc])

    # Financiero
    tokens_reserve_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('20.00'))
    banco = models.CharField(max_length=100, blank=True)
    cuenta_bancaria = models.CharField(max_length=50, blank=True)
    tipo_cuenta = models.CharField(max_length=20, blank=True)

    kyb_revisado_por = models.ForeignKey('auth.User', null=True, blank=True,
                                         on_delete=models.SET_NULL,
                                         related_name='kyb_revisiones')
    kyb_fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    kyb_notas = models.TextField(blank=True)  # notas internas Joan

    class Meta:
        indexes = [models.Index(fields=['kyb_estado'])]

    def __str__(self):
        return f"Fraccionador {self.user.username} ({self.kyb_estado})"
