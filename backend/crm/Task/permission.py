from accounts.permissions import HasDynamicPermission


class CanCommunicateWithLead(HasDynamicPermission):
    """
    Reuses Member 1's dynamic RBAC permission system.

    Each CRM view will define its own `permission_names`
    mapping, for example:

        permission_names = {
            "GET": "view_task",
            "POST": "add_task",
            "PATCH": "change_task",
            "DELETE": "delete_task",
        }

    The actual permission check is handled by
    accounts.permissions.HasDynamicPermission.
    """

    pass
