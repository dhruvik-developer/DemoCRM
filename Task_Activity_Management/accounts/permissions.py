from rest_framework.permissions import BasePermission


class HasDynamicPermission(BasePermission):

    permission_name = None

    def has_permission(self, request, view):

        if not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        role = request.user.role

        if role is None:
            return False

        return role.permissions.filter(
            codename=self.permission_name
        ).exists()
    