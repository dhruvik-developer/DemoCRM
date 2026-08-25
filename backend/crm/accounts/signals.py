"""
Auto-seed default role permissions after every migrate.

Admin    -> all permissions.
Manager  -> full management of Task / Meeting / Reminder / FollowUp /
            Notification (+ custom assign_task, send_notification).
Employee -> read access plus the actions an assignee needs
            (change task status, add reminders/followups, read/mark
            notifications).

The receiver runs for every app's post_migrate and is idempotent, so a
partial migrate (e.g. `migrate Task`) still converges once all
permissions exist.
"""

from django.contrib.auth.models import Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import Role


def _codename_set(prefixes):
    # Django default permission codenames are <action>_<model>, e.g. view_task.
    return {
        f"{action}_{prefix}"
        for prefix in prefixes
        for action in ("view", "add", "change", "delete")
    }


# Models the Manager role can fully manage.
MANAGER_MODEL_PREFIXES = [
    "task",
    "taskstatus",
    "taskpriority",
    "taskcategory",
    "meeting",
    "meetingstatus",
    "meetingtype",
    "meetingparticipant",
    "reminder",
    "remindertype",
    "reminderstatus",
    "followup",
    "followupnote",
    "followupstatus",
    "followuptypes",
    "notification",
    "notificationtemplate",
    "notificationtype",
    "calltemplate",
    "templateversion",
    "templatefield",
    "pipelinestageactivity",
    "callattempt",
    "formsubmission",
    "tasktriggerrule",
    "customeraccount",
    "customercontact",
    "customer",
    "adhocfieldproposal",
    "indexedsubmissionvalue",
]

MANAGER_CODENAMES = _codename_set(MANAGER_MODEL_PREFIXES) | {
    "assign_task",
    "send_notification",
    # CallForms / customer-management custom permissions declared in model
    # Meta.permissions so managers can exercise them without manual grants.
    "manage_call_template",
    "manage_template_version",
    "manage_template_field",
    "manage_stage_activity",
    "add_adhoc_field",
    "manage_adhoc_field",
}

# Models the Employee role can read.
EMPLOYEE_MODEL_PREFIXES = [
    "task",
    "taskstatus",
    "taskpriority",
    "taskcategory",
    "meeting",
    "meetingstatus",
    "meetingtype",
    "meetingparticipant",
    "reminder",
    "remindertype",
    "reminderstatus",
    "followup",
    "followupnote",
    "followupstatus",
    "followuptypes",
    "notification",
    "notificationtemplate",
    "notificationtype",
    "calltemplate",
    "templateversion",
    "templatefield",
    "pipelinestageactivity",
    "callattempt",
    "formsubmission",
    "tasktriggerrule",
    "customeraccount",
    "customercontact",
    "customer",
    "adhocfieldproposal",
    "indexedsubmissionvalue",
]

EMPLOYEE_CODENAMES = {f"view_{prefix}" for prefix in EMPLOYEE_MODEL_PREFIXES} | {
    # An assignee can act on their own tasks / add their own records.
    "change_task",
    "add_meeting",
    "add_meetingparticipant",
    "delete_meetingparticipant",
    "add_reminder",
    "change_reminder",
    "delete_reminder",
    "add_followup",
    "add_followupnote",
    "change_notification",
    "add_callattempt",
    "change_callattempt",
    "add_formsubmission",
    "change_formsubmission",
    "add_adhoc_field",
}

DEFAULT_ROLE_PERMISSIONS = {
    "Admin": None,  # None means: all permissions.
    "Manager": MANAGER_CODENAMES,
    "Employee": EMPLOYEE_CODENAMES,
}


@receiver(post_migrate)
def seed_default_role_permissions(sender, **kwargs):
    using = kwargs.get("using", "default")
    all_permissions = Permission.objects.using(using).all()

    for rolename, codenames in DEFAULT_ROLE_PERMISSIONS.items():
        role, _ = Role.objects.using(using).get_or_create(rolename=rolename)

        if codenames is None:
            permissions = all_permissions
        else:
            permissions = all_permissions.filter(codename__in=codenames)

        role.permissions.add(*permissions)
