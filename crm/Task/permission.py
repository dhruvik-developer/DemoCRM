#from rest_framework.permissions import BasePermission
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

class CanCommunicateWithLead(HasDynamicPermission):
    # message = "Only the lead owner, task assignee, creator, or manager can communicate with this record."

    # def has_object_permission(self, request, view, obj):
    #     user = request.user
    #     if not user or not user.is_authenticated:
    #         return False
    #     if user.is_superuser or is_manager(user):
    #         return True

    #     # If obj is Task or has assigned_to / created_by
    #     if getattr(obj, "created_by", None) == user or getattr(obj, "assigned_to", None) == user:
    #         return True

    #     # If obj has task_id (e.g. Meeting or Reminder)
    #     task = getattr(obj, "task_id", None)
    #     if task:
    #         if getattr(task, "assigned_to", None) == user or getattr(task, "created_by", None) == user:
    #             return True

    #     # If obj is Meeting with participants
    #     if hasattr(obj, "participants"):
    #         if obj.participants.filter(user_id=user).exists():
    #             return True

    #     # If obj has meeting_id (e.g. Reminder)
    #     meeting = getattr(obj, "meeting_id", None)
    #     if meeting:
    #         if getattr(meeting, "created_by", None) == user:
    #             return True
    #         if hasattr(meeting, "participants") and meeting.participants.filter(user_id=user).exists():
    #             return True
    #         meeting_task = getattr(meeting, "task_id", None)
    #         if meeting_task:
    #             if getattr(meeting_task, "assigned_to", None) == user or getattr(meeting_task, "created_by", None) == user:
    #                 return True

    #     # If obj has reminder_for
    #     if getattr(obj, "reminder_for", None) == user:
    #         return True

    #     # Lead check
    #     lead = getattr(obj, "lead", None)
    #     if lead is None:
    #         lead = getattr(obj, "lead_id", None)
    #     if lead is None and task:
    #         lead = getattr(task, "lead", None)
    #     if lead is None and meeting:
    #         lead = getattr(meeting, "lead", None)
    #     if lead:
    #         lead_owner = getattr(lead, "assigned_to", None)
    #         if lead_owner == user:
    #             return True

    #     return False
    pass