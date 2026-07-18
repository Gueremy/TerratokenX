# Re-exporta las vistas legacy (templates server-side) y los módulos nuevos.
from .legacy import *  # noqa: F401,F403
from . import payments  # noqa: F401
