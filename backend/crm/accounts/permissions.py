import logging

from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class HasDynamicPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        role = request.user.role

        if role is None:
            logger.warning(
                "Access denied for user %s: No role assigned",
                getattr(request.user, "user_id", request.user),
            )
            return False

        permission_config = getattr(view, "permission_names", None) or getattr(
            view, "permission_name", None
        )

        if permission_config is None:
            logger.warning(
                "Access denied for view %s: No permission configuration defined",
                view.__class__.__name__,
            )
            return False

        if isinstance(permission_config, dict):
            required_permission = permission_config.get(request.method)
        else:
            required_permission = permission_config

        if not required_permission:
            logger.warning(
                "Access denied for view %s %s: No permission mapped for method",
                request.method,
                view.__class__.__name__,
            )
            return False

        if isinstance(required_permission, (list, tuple, set)):
            # A view may allow any one of several permissions, for example
            # add_followup for employees or change_followup for managers.
            has_perm = role.permissions.filter(
                codename__in=required_permission
            ).exists()
            required_permission_label = " or ".join(required_permission)
        else:
            has_perm = role.permissions.filter(codename=required_permission).exists()
            required_permission_label = required_permission

        if not has_perm:
            logger.warning(
                "Access denied for user %s (Role: %s) on %s %s: Required codename '%s' missing",
                getattr(request.user, "user_id", request.user),
                role.rolename,
                request.method,
                request.path,
                required_permission_label,
            )

        return has_perm
