"""
Shared helpers for:
  1. Creating an in-system Notification row for a user.
  2. Sending a plain reminder/notification email.
  3. Rendering NotificationTemplate placeholders.
"""

import re
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Notification, NotificationTemplate, NotificationType

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
logger = logging.getLogger(__name__)



def render_template(template, context):
    """Replace {{placeholder}} tokens in template subject/body.

    Unknown placeholders are left as-is so the admin can still see them
    in the editable preview and fill them in manually.
    """
    context = context or {}

    def replace(match):
        key = match.group(1)
        value = context.get(key)
        if value is None:
            return match.group(0)
        return str(value)

    return (
        PLACEHOLDER_RE.sub(replace, template.subject),
        PLACEHOLDER_RE.sub(replace, template.body),
    )


def build_context(user, task=None, followup=None):
    """Build the placeholder context for a single recipient."""
    context = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name(),
        "email": user.email,
    }

    if task is not None:
        context.update(
            {
                "task_title": task.task_title,
                "due_date": task.due_date,
                "task_status": getattr(task.status, "status_name", None),
            }
        )

    if followup is not None:
        context.update(
            {
                "followup_date": followup.followup_date,
                "followup_status": getattr(
                    followup.followup_status, "status_name", None
                ),
            }
        )

    return context


def render_notification_preview(template, user, task=None, followup=None):
    return render_template(template, build_context(user, task, followup))


def create_notification(
    user,
    title,
    message,
    type_name="System",
    template=None,
    scheduled_at=None,
    edited_by=None,
    is_customized=False,
):
    if user is None:
        return None

    notification_type, _ = NotificationType.objects.get_or_create(
        type_name=type_name
    )

    if template is None:
        template, _ = NotificationTemplate.objects.get_or_create(
            subject=title,
            defaults={"body": message},
        )

    status = Notification.Status.SCHEDULED if scheduled_at else Notification.Status.DRAFT

    return Notification.objects.create(
        user_id=user,
        notification_type_id=notification_type,
        template_id=template,
        title=title,
        message=message,
        status=status,
        scheduled_at=scheduled_at,
        edited_by=edited_by,
        is_customized=is_customized,
    )


def send_notification_email(notification):
    """Email a single notification to its recipient and mark it as sent."""
    recipient = notification.user_id

    if recipient is None or not recipient.email:
        notification.status = Notification.Status.FAILED
        notification.save(update_fields=["status"])
        return False

    send_reminder_email(
        subject=notification.title,
        message=notification.message,
        recipient_list=[recipient.email],
    )

    notification.status = Notification.Status.SENT
    notification.sent_at = timezone.now()
    notification.save(update_fields=["status", "sent_at"])
    return True


def send_reminder_email(subject, message, recipient_list):
    recipient_list = [email for email in recipient_list if email]

    if not recipient_list:
        return

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@democrm.local"),
        recipient_list=recipient_list,
        fail_silently=True,
    )


# =============================================================================
# AUTOMATED TASK ASSIGNMENT NOTIFICATION
# =============================================================================

TASK_ASSIGNMENT_TEMPLATE_NAME = "Task Assignment"


def get_task_assignment_template():
    """Return (template, notification_type) for task assignment messages.

    Creates the template on first use so the feature works out of the box
    and stays editable from the template admin/list.
    """
    notification_type, _ = NotificationType.objects.get_or_create(
        type_name="Task"
    )

    template = NotificationTemplate.objects.filter(
        name=TASK_ASSIGNMENT_TEMPLATE_NAME,
    ).first()

    if template is None:
        template = NotificationTemplate.objects.create(
            name=TASK_ASSIGNMENT_TEMPLATE_NAME,
            notification_type_id=notification_type,
            subject="New task assigned: {{task_title}}",
            body=(
                "Hi {{first_name}},\n\n"
                "This task is assigned to you by {{assigner_name}}.\n\n"
                "Task: {{task_title}}\n"
                "Due date: {{due_date}}"
            ),
        )

    return template, notification_type


def notify_task_assignment(task):
    """Send the auto task-assignment notification to the assignee."""
    recipient = task.assigned_to

    if recipient is None:
        return None

    context = build_context(recipient, task=task)
    context["assigner_name"] = (
        task.created_by.get_full_name() or task.created_by.email
    )

    template, notification_type = get_task_assignment_template()
    subject, body = render_template(template, context)

    notification = create_notification(
        user=recipient,
        title=subject,
        message=body,
        type_name=notification_type.type_name,
        template=template,
    )

    send_notification_email(notification)
    return notification