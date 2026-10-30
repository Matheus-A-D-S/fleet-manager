from rest_framework.permissions import SAFE_METHODS, BasePermission


def _is_manager(user):
    return bool(user and user.is_authenticated and user.role in ("ADMIN", "MANAGER"))


class IsManager(BasePermission):
    """Apenas administradores e gestores."""

    def has_permission(self, request, view):
        return _is_manager(request.user)


class IsManagerOrReadOnly(BasePermission):
    """Qualquer usuário autenticado lê; só gestores/admin escrevem."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or _is_manager(request.user)
