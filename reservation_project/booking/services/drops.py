from django.utils import timezone
from django.db.models import Sum
from booking.models import Drop, Reserva

def get_current_drop(proyecto):
    """Retorna el Drop activo actual para un proyecto, o None."""
    now = timezone.now()
    return proyecto.drops.filter(activo=True, fecha_inicio__lte=now, fecha_fin__gte=now).first()

def check_stock_availability(drop, cantidad_tokens_intentada):
    """
    Verifica si el Drop actual tiene suficiente stock asignado disponible.
    Regla: Cada Drop tiene un % del stock total del proyecto.
    """
    proyecto = drop.proyecto
    stock_total_proyecto = proyecto.tokens_totales
    
    # Stock asignado a este Drop específico
    stock_drop = int((stock_total_proyecto * drop.porcentaje_stock) / 100)
    
    # Calcular cuánto se ha vendido DURANTE este Drop
    # (Tokens vendidos en reservas confirmadas creadas dentro de las fechas del drop)
    tokens_vendidos_en_drop = Reserva.objects.filter(
        proyecto=proyecto,
        estado_pago='CONFIRMADO',
        created_at__range=(drop.fecha_inicio, drop.fecha_fin)
    ).aggregate(Sum('cantidad_tokens'))['cantidad_tokens__sum'] or 0
    
    stock_disponible_drop = stock_drop - tokens_vendidos_en_drop
    
    if cantidad_tokens_intentada > stock_disponible_drop:
        return False, stock_disponible_drop
        
    return True, stock_disponible_drop
