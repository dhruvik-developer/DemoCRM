from accounts.permissions import HasDynamicPermission


class CRMHasPermission(HasDynamicPermission):
    """
    Reuses Member 1's dynamic RBAC permission system.

    Each CRM view will define its own `permission_names`
    mapping, for example:

        permission_names = {
            "GET": "view_lead",
            "POST": "create_lead",
            "PUT": "update_lead",
            "PATCH": "update_lead",
            "DELETE": "delete_lead",
        }

    The actual permission check is handled by
    accounts.permissions.HasDynamicPermission.
    """

    pass