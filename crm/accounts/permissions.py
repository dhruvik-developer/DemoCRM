from rest_framework.permissions import BasePermission


class HasDynamicPermission(BasePermission):

    permission_names = None

    def has_permission(self, request, view):

        if not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        role = request.user.role

        if role is None:
            return False

        permission_names = getattr(view, "permission_names", None)

        if permission_names is None:
            return False

        return role.permissions.filter(
            codename=permission_names
        ).exists()