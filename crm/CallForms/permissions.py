from accounts.permissions import HasDynamicPermission


class CallFormsHasPermission(HasDynamicPermission):
    """
    RBAC Permission class for CallForms app.
    Checks user.role.permissions dynamically against view's permission_names configuration.
    """

    pass
