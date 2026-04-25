
# --- PERFIL DE USUARIO PARA KYC (NUEVO) ---
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    
    # Niveles de KYC
    KYC_TIER_CHOICES = [
        (0, 'Nivel 0 - Básico (Hasta $500)'),
        (1, 'Nivel 1 - Verificado (Hasta $10k)'),
        (2, 'Nivel 2 - Avanzado (Ilimitado)'),
    ]
    kyc_tier = models.PositiveSmallIntegerField(
        default=0, 
        choices=KYC_TIER_CHOICES,
        help_text="Nivel de verificación actual del usuario."
    )
    
    # Status de la verificación
    KYC_STATUS_CHOICES = [
        ('UNVERIFIED', 'No Verificado'),
        ('PENDING', 'En Revisión'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado'),
    ]
    kyc_status = models.CharField(
        max_length=20, 
        choices=KYC_STATUS_CHOICES, 
        default='UNVERIFIED',
        help_text="Estado de la solicitud de KYC."
    )
    
    # Documentos (Simulación MVP)
    dni_front = models.ImageField(upload_to='kyc_docs/', blank=True, null=True, help_text="Foto frontal del DNI")
    dni_back = models.ImageField(upload_to='kyc_docs/', blank=True, null=True, help_text="Foto trasera del DNI")
    proof_of_address = models.FileField(upload_to='kyc_docs/', blank=True, null=True, help_text="Comprobante de domicilio (PDF/Img)")
    
    # Acumulado para saber cuánto ha invertido (Cache, se recalcula al comprar)
    investment_total_usd = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="Total invertido en USD acumulado."
    )
    
    def __str__(self):
        return f"{self.user.username} - Tier {self.kyc_tier}"

    @property
    def limit_usd(self):
        """Retorna el límite de inversión en USD según el nivel"""
        if self.kyc_tier == 0: return 500
        if self.kyc_tier == 1: return 10000
        return 999999999 # Ilimitado

    @property
    def remaining_limit(self):
        """Cuánto cupo le queda para invertir antes de bloquearse"""
        return max(0, float(self.limit_usd) - float(self.investment_total_usd))

# Signal para crear perfil automáticamente
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
