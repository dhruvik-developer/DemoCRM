from accounts.permissions import HasDynamicPermission


class CanCommunicateWithlead(HasDynamicPermission):
    """
    Reuses Member 1's dynamic RBAC permission system.

    Each CRM view will define its own `permission_names`
    mapping, for example:

        permission_names = {
            "GET": "view_followup",
            "POST": "add_followup",
            "PATCH": "change_followup",
            "DELETE": "delete_followup",
        }

    The actual permission check is handled by
    accounts.permissions.HasDynamicPermission.
    """

    pass
