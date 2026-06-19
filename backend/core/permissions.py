from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsNurse(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.role == "NURSE" or request.user.role == "ADMIN"))


class IsDoctor(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.role == "DOCTOR" or request.user.role == "ADMIN"))


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "ADMIN")


class IsAdminOrReadOnly(BasePermission):
    """Reference/lookup data: any authenticated staff can read, only admin can write."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.role == "ADMIN"
