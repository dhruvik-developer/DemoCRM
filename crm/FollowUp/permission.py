from rest_framework.permissions import BasePermission

def is_manager(user):
    if not user or not user.is_authneticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user,"role",None)
    if not role:
        return False
    role_name = getattr(role,"role_name","")
    return role_name.strip().lower()=="manager"

def get_followup_lead(followup):
    task = getattr(followup,"task_id",None)
    if not task:
        return None
    return getattr(task,"lead",None)

class CanCommunicateWithlead(BasePermission):
    message = (
        "only the lead owner or manager",
        "can access this followup"
    )
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        if is_manager(user):
            return True
        lead = get_followup_lead(obj)
        if not lead:
            return False
        lead_owner = getattr(lead,"assigned_to",None)
        return lead_owner == user 