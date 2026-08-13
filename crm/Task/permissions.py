from accounts.permissions import HasDynamicPermission


class TaskHasPermission(HasDynamicPermission):
    """
    Reuses the dynamic RBAC permission system.

    Each Task view defines its own `permission_names` mapping,
    e.g.:

        permission_names = {
            "GET": "view_task",
            "POST": "add_task",
            "PATCH": "change_task",
            "DELETE": "delete_task",
        }

    The actual check is handled by
    accounts.permissions.HasDynamicPermission.
    """

    pass
