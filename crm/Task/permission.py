from rest_framework.permissions import BasePermission

class CanCommunicateWithLead(BasePermission):
    message = (
        "only the lead owner or manager can ",
        "communicate with lead"
    )
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        role = getattr(user,'role',None)
        role_name = getattr(role,"role_name","")
        if role_name.strip().lower() == "manager":
            return True
        lead = getattr(obj,"lead",None)
        if lead is None:
            lead = getattr(obj,"lead_id",None)
        if lead is None:
            meeting = getattr(obj,"meeting_id",None)
            if meeting:
                lead = getattr(meeting,"lead",None)
        if not lead:
            return False
        lead_owner = getattr(lead,"assigned_to",None)
        return lead_owner == user