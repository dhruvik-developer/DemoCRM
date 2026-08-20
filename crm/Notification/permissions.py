import logging
from accounts.permissions import HasDynamicPermission

logger = logging.getLogger(__name__)


class NotificationHasPermission(HasDynamicPermission):
    """
    Permission class for Notification app:
    - Superusers have full access.
    - Admin and Manager roles have template management and manual notification access.
    - Authenticated users can view/read their own notifications.
    - Checks user.role.permissions for dynamic codename matching if configured.
    """

    # def has_permission(self, request, view):
    #     if not request.user or not request.user.is_authenticated:
    #         return False

    #     if request.user.is_superuser:
    #         return True

    #     role = getattr(request.user, "role", None)
    #     role_name = role.rolename if role else ""

    #     # Default role-based access for notification templates & manual sending
    #     permission_config = getattr(view, "permission_names", None) or getattr(view, "permission_name", None)

    #     if permission_config:
    #         if isinstance(permission_config, dict):
    #             required_perm = permission_config.get(request.method)
    #         else:
    #             required_perm = permission_config

    #         if required_perm and role:
    #             if role.permissions.filter(codename=required_perm).exists():
    #                 return True

    #     # Fallback role checks
    #     if role_name in ["Admin", "Manager"]:
    #         return True

    #     # Employees can access User Notification endpoints
    #     if view.__class__.__name__ in [
    #         "UserNotificationListView",
    #         "UserNotificationDetailView",
    #         "NotificationMarkReadView",
    #     ]:
    #         return True

    #     return False

    pass
