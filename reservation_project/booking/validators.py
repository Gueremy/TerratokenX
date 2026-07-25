"""Validación y saneamiento de archivos subidos.

Aplica a documentos KYC (cédulas, selfies), KYB (escrituras, tasaciones),
imágenes de proyectos y documentos del data room.

Reglas (docs/core/seguridad.md §6):
- Solo tipos explícitamente permitidos (nunca HTML/SVG: se sirven como XSS).
- Tamaño máximo acotado.
- El nombre original del usuario NUNCA se usa en disco (path traversal).
"""

import os
import uuid

from django.core.exceptions import ValidationError

MAX_FILE_SIZE_MB = 10

# Documentos de identidad y legales
TIPOS_KYC = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
EXTENSIONES_KYC = ['.jpg', '.jpeg', '.png', '.webp', '.pdf']

# Imágenes públicas (portadas, galerías)
TIPOS_IMAGEN = ['image/jpeg', 'image/png', 'image/webp']
EXTENSIONES_IMAGEN = ['.jpg', '.jpeg', '.png', '.webp']


def _validar(archivo, tipos_permitidos, extensiones_permitidas, etiqueta):
    if archivo is None:
        return

    tamano = getattr(archivo, 'size', 0) or 0
    if tamano > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValidationError(
            f'El archivo supera el máximo de {MAX_FILE_SIZE_MB} MB.'
        )
    if tamano == 0:
        raise ValidationError('El archivo está vacío.')

    content_type = (getattr(archivo, 'content_type', '') or '').lower().split(';')[0].strip()
    if content_type and content_type not in tipos_permitidos:
        raise ValidationError(
            f'Tipo de archivo no permitido para {etiqueta}. '
            f'Formatos aceptados: {", ".join(extensiones_permitidas)}.'
        )

    # La extensión también se valida: el content_type lo declara el cliente.
    nombre = getattr(archivo, 'name', '') or ''
    extension = os.path.splitext(nombre)[1].lower()
    if extension and extension not in extensiones_permitidas:
        raise ValidationError(
            f'Extensión "{extension}" no permitida para {etiqueta}. '
            f'Formatos aceptados: {", ".join(extensiones_permitidas)}.'
        )


def validar_archivo_kyc(archivo):
    """Documentos de identidad y legales: imágenes o PDF, máximo 10 MB."""
    _validar(archivo, TIPOS_KYC, EXTENSIONES_KYC, 'documentos')


def validar_imagen(archivo):
    """Imágenes públicas de proyectos: solo formatos de imagen, máximo 10 MB."""
    _validar(archivo, TIPOS_IMAGEN, EXTENSIONES_IMAGEN, 'imágenes')


def nombre_seguro(nombre_original: str) -> str:
    """
    Devuelve un nombre aleatorio conservando solo la extensión.
    Nunca reutiliza el nombre del usuario: evita path traversal y colisiones.
    """
    extension = os.path.splitext(nombre_original or '')[1].lower()
    if extension not in EXTENSIONES_KYC + EXTENSIONES_IMAGEN:
        extension = ''
    return f"{uuid.uuid4().hex}{extension}"


# ── Rutas de subida ──────────────────────────────────────────────────────────
# Django serializa `upload_to` en las migraciones, así que deben ser funciones
# a nivel de módulo (no closures). Todas descartan el nombre original.

def ruta_kyc_documentos(instance, filename):
    return f"kyc/documentos/{nombre_seguro(filename)}"


def ruta_kyc_selfies(instance, filename):
    return f"kyc/selfies/{nombre_seguro(filename)}"


def ruta_kyb_dominios(instance, filename):
    return f"kyb/dominios/{nombre_seguro(filename)}"


def ruta_kyb_escrituras(instance, filename):
    return f"kyb/escrituras/{nombre_seguro(filename)}"


def ruta_kyb_tasaciones(instance, filename):
    return f"kyb/tasaciones/{nombre_seguro(filename)}"


def ruta_proyectos(instance, filename):
    return f"proyectos/{nombre_seguro(filename)}"


def ruta_proyectos_galeria(instance, filename):
    return f"proyectos/galeria/{nombre_seguro(filename)}"


def ruta_proyectos_documentos(instance, filename):
    return f"proyectos/documentos/{nombre_seguro(filename)}"
