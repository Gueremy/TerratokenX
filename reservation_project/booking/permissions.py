from rest_framework.permissions import BasePermission


class IsFraccionador(BasePermission):
    """Solo usuarios del grupo Fractionalizer."""
    message = 'Se requiere cuenta de fraccionador verificada.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.groups.filter(name='Fractionalizer').exists()
        )


class EsDuenioDelProyecto(BasePermission):
    """A nivel de objeto: solo el dueño puede ver/editar su proyecto."""
    message = 'No tienes permiso para acceder a este proyecto.'

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsJoanAdmin(BasePermission):
    """Solo Joan (superuser o grupo JoanAdmin)."""
    message = 'Acceso restringido al administrador.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.groups.filter(name='JoanAdmin').exists()
            )
        )
