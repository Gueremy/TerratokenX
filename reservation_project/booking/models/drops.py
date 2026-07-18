from django.db import models


class ProjectDrop(models.Model):
    """Ventana de venta con stock limitado y tiempo definido (estructura 30/30/40)."""
    proyecto = models.ForeignKey('booking.Proyecto', on_delete=models.CASCADE, related_name='drops')
    nombre = models.CharField(max_length=100)   # "Drop 1", "Drop 2", "Drop 3"
    numero = models.IntegerField()              # 1, 2, 3
    stock_total = models.IntegerField()
    stock_disponible = models.IntegerField()
    precio_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    activo = models.BooleanField(default=False)

    class Meta:
        unique_together = [['proyecto', 'numero']]
        indexes = [models.Index(fields=['proyecto', 'activo'])]

    def __str__(self):
        return f"{self.proyecto.nombre} — {self.nombre}"
