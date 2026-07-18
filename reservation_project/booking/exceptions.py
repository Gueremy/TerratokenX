class DropInactivo(Exception):
    """No hay Drop activo para este proyecto."""
    pass


class StockInsuficiente(Exception):
    """El Drop no tiene suficiente stock para la cantidad solicitada."""
    pass


class LimiteKYCSuperado(Exception):
    """El usuario superaría su límite KYC con esta compra."""
    pass


class CreditoInsuficiente(Exception):
    """Saldo de créditos insuficiente para la operación."""
    pass


class DropYaCerrado(Exception):
    """El Drop ya fue cerrado o está fuera de su ventana de tiempo."""
    pass


class IdempotenciaError(Exception):
    """La operación ya fue procesada anteriormente."""
    pass


class BlockchainTransactionFailed(Exception):
    """La transacción on-chain falló (Fase 3)."""
    pass
