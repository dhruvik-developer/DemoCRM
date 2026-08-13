from accounts.permissions import HasDynamicPermission


class FollowUpHasPermission(HasDynamicPermission):
    """
    Reuses the dynamic RBAC permission system.

    Each FollowUp view defines its own `permission_names` mapping,
    e.g.:

        permission_names = {
            "GET": "view_followup",
            "POST": "add_followup",
            "PATCH": "change_followup",
            "DELETE": "delete_followup",
        }

    The actual check is handled by
    accounts.permissions.HasDynamicPermission.
    """

    pass
