from rest_framework.permissions import BasePermission


class HasDynamicPermission(BasePermission):

    def has_permission(self, request, view):

        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        role = request.user.role

        if role is None:
            return False

        permission_config = getattr(view, "permission_names", None) or getattr(view, "permission_name", None)

        if permission_config is None:
            return False

        if isinstance(permission_config, dict):
            required_permission = permission_config.get(request.method)
        else:
            required_permission = permission_config

        if not required_permission:
            return False

        return role.permissions.filter(
            codename=required_permission
        ).exists()