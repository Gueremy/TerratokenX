from rest_framework.response import Response


def error_response(code: str, message: str, status: int = 400) -> Response:
    """Formato estándar de error de la API: {'error': codigo, 'message': texto}."""
    return Response({'error': code, 'message': message}, status=status)
