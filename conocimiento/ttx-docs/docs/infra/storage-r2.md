# Storage — Cloudflare R2

## Por qué no Render

Los discos de Render son **efímeros**. Cada redeploy o restart limpia el filesystem.
Cualquier archivo subido (KYC, imágenes de proyectos, Data Room) desaparece.

Cloudflare R2 es S3-compatible, tiene 0 egress fees (S3 cobra por salida de datos)
y 10GB gratis al mes. Es la solución correcta para TerraTokenX.

---

## ⚙️ CREDENCIALES REQUERIDAS

```
Antes de implementar esta sección, decirle a Gueremy:
"Necesito las credenciales de Cloudflare R2 para continuar."

□ R2_ACCESS_KEY_ID
□ R2_SECRET_ACCESS_KEY
□ R2_BUCKET_NAME       → nombre del bucket (ej: terratokenx-files)
□ R2_ENDPOINT_URL      → https://<ACCOUNT_ID>.r2.cloudflarestorage.com

Obtener en: https://dash.cloudflare.com → R2 → Overview
→ "Manage R2 API Tokens" → Create API Token
→ Permisos: Object Read & Write
→ El Account ID está en la URL del dashboard
```

---

## Configuración

```bash
pip install django-storages boto3
```

```python
# settings/base.py
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_S3_ENDPOINT_URL      = config('R2_ENDPOINT_URL')
AWS_ACCESS_KEY_ID        = config('R2_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY    = config('R2_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME  = config('R2_BUCKET_NAME')
AWS_S3_REGION_NAME       = 'auto'
AWS_DEFAULT_ACL          = 'private'
AWS_S3_FILE_OVERWRITE    = False
AWS_QUERYSTRING_AUTH     = True    # URLs firmadas (no públicas por defecto)
AWS_QUERYSTRING_EXPIRE   = 3600    # URLs firmadas válidas por 1 hora
```

```python
# settings/local.py — en desarrollo, guardar localmente
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL  = '/media/'
```

---

## Estructura de carpetas en el bucket

```
terratokenx-files/
├── kyc/
│   ├── documentos/     ← cédulas, pasaportes verificados por Didit
│   └── selfies/        ← (Didit maneja esto internamente — no almacenar en R2)
├── kyb/
│   ├── dominios/       ← Certificado de Dominio Vigente
│   ├── escrituras/     ← Escrituras públicas
│   └── tasaciones/     ← Tasaciones profesionales
├── proyectos/
│   ├── imagenes/       ← Fotos de los terrenos
│   └── portadas/       ← Imagen principal del proyecto
├── dataroom/
│   └── <proyecto_id>/  ← Documentos del Data Room por proyecto
└── backups/
    └── db/             ← Backups diarios de PostgreSQL
```

---

## Naming seguro de archivos

```python
# booking/utils.py
import uuid, os


def get_safe_upload_path(folder: str, filename: str) -> str:
    """
    Genera path seguro para uploads.
    NUNCA usar el nombre original del usuario (path traversal).
    """
    ext = os.path.splitext(filename)[1].lower()
    safe_ext = ext if ext in ['.jpg', '.jpeg', '.png', '.pdf', '.webp'] else '.bin'
    return f"{folder}/{uuid.uuid4()}{safe_ext}"


# Uso en modelos:
class ProyectoImagen(models.Model):
    imagen = models.ImageField(
        upload_to=lambda instance, filename: get_safe_upload_path('proyectos/imagenes', filename)
    )
```

---

## URLs firmadas para Data Room

```python
# booking/selectors.py

import boto3
from django.conf import settings


def get_signed_url_dataroom(s3_key: str, expiry_seconds: int = 3600) -> str:
    """
    Genera URL temporal para descargar un documento del Data Room.
    Solo inversores con reserva CONFIRMADA del proyecto deben obtener esta URL.
    """
    s3 = boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name='auto',
    )
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': s3_key},
        ExpiresIn=expiry_seconds,
    )
    return url
```
