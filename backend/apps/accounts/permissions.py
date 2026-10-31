from rest_framework.permissions import SAFE_METHODS, BasePermission


def _has_org(user):
    return bool(user and user.is_authenticated and user.organization_id)


def _is_manager(user):
    return _has_org(user) and user.role in ("ADMIN", "MANAGER")


class IsTenantMember(BasePermission):
    """Autenticado e vinculado a uma empresa (padrão da API)."""

    def has_permission(self, request, view):
        return _has_org(request.user)


class IsManager(BasePermission):
    """Administradores e gestores da empresa."""

    def has_permission(self, request, view):
        return _is_manager(request.user)


class IsOrgAdmin(BasePermission):
    """Somente administradores da empresa (gestão de usuários)."""

    def has_permission(self, request, view):
        return _has_org(request.user) and request.user.role == "ADMIN"


class IsManagerOrReadOnly(BasePermission):
    """Qualquer membro da empresa lê; só gestores/admin escrevem."""

    def has_permission(self, request, view):
        if not _has_org(request.user):
            return False
        return request.method in SAFE_METHODS or _is_manager(request.user)
