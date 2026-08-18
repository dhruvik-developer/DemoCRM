from rest_framework.permissions import BasePermission
from accounts.permissions import HasDynamicPermission

# def is_manager(user):
#     if not user or not user.is_authenticated:
#         return False
#     if user.is_superuser:
#         return True
#     role = getattr(user, "role", None)
#     if not role:
#         return False
#     role_name = getattr(role, "rolename", getattr(role, "role_name", ""))
#     return str(role_name).strip().lower() == "manager"

# def get_followup_lead(followup):
#     task = getattr(followup, "task_id", None)
#     if not task:
#         return None
#     return getattr(task, "lead", None)

class CanCommunicateWithlead(HasDynamicPermission):
#     message = "Only the lead owner, assigned employee, creator, or manager can access this follow-up."

#     def has_object_permission(self, request, view, obj):
#         user = request.user
#         if not user or not user.is_authenticated:
#             return False
#         if user.is_superuser or is_manager(user):
#             return True

#         # Followup creator
#         if getattr(obj, "created_by", None) == user:
#             return True

#         # Task assignee or creator
#         task = getattr(obj, "task_id", None)
#         if task is None and hasattr(obj, "followup_id"):
#             followup = getattr(obj, "followup_id", None)
#             if followup:
#                 task = getattr(followup, "task_id", None)
#                 if getattr(followup, "created_by", None) == user:
#                     return True

#         if task:
#             if getattr(task, "assigned_to", None) == user or getattr(task, "created_by", None) == user:
#                 return True

#         # Lead owner
#         lead = get_followup_lead(obj)
#         if lead is None and hasattr(obj, "followup_id"):
#             followup = getattr(obj, "followup_id", None)
#             if followup:
#                 lead = get_followup_lead(followup)

#         if lead:
#             lead_owner = getattr(lead, "assigned_to", None)
#             if lead_owner == user:
#                 return True

#         return False

# CanCommunicateWithLead = CanCommunicateWithlead
    pass