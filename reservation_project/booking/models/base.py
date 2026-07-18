from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    """Base para modelos con datos financieros: nunca se borran físicamente."""
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # incluye borrados — usar en admin y auditoría

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def hard_delete(self, *args, **kwargs):
        """Solo para tests y limpieza de datos de prueba."""
        super().delete(*args, **kwargs)

    class Meta:
        abstract = True
