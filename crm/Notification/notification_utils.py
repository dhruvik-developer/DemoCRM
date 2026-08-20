import logging
import re
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from .models import Notification, NotificationChannel, NotificationTemplate

logger = logging.getLogger(__name__)

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def render_template(template_str, context):
    """Replace {{variable}} placeholders in template string using context dictionary."""
    if not template_str:
        return ""
    context = context or {}

    def replace(match):
        key = match.group(1)
        value = context.get(key)
        if value is None:
            return match.group(0)
        return str(value)

    return PLACEHOLDER_RE.sub(replace, template_str)


def trigger_notification_event(
    event_type,
    recipient,
    context=None,
    template_id=None,
    custom_message=None,
    channel=None,
):
    """
    Central event-based notification trigger.
    Can be called by any CRM module (Task, FollowUp, Quotation, Accounts).

    :param event_type: Event identifier (e.g. TASK_ASSIGNED, QUOTATION_APPROVED)
    :param recipient: Single CustomUser or iterable of CustomUsers
    :param context: Dict with dynamic placeholder variables
    :param template_id: Optional explicit template ID
    :param custom_message: Optional manual message override
    :param channel: Optional channel override (IN_APP, EMAIL, BOTH)
    :return: List of created Notification instances
    """
    try:
        if recipient is None:
            return []

        if not isinstance(recipient, (list, tuple, set, QuerySet if 'QuerySet' in locals() else type(None))):
            try:
                from django.db.models.query import QuerySet
                if isinstance(recipient, QuerySet):
                    recipients = list(recipient)
                else:
                    recipients = [recipient]
            except ImportError:
                recipients = [recipient]
        else:
            recipients = list(recipient)

        recipients = [u for u in recipients if u is not None]
        if not recipients:
            return []

        context = context or {}

        # 1. Find matching active template
        template = None
        try:
            if template_id:
                template = NotificationTemplate.objects.filter(
                    pk=template_id, is_active=True
                ).first()

            if template is None:
                templates = NotificationTemplate.objects.filter(
                    event_type=event_type, is_active=True
                )
                template = templates.filter(is_default=True).first() or templates.first()
        except Exception as e:
            logger.error("Failed to fetch notification template for event '%s': %s", event_type, e)
            template = None

        # 2. Render final message
        if custom_message:
            final_message = render_template(custom_message, context)
        elif template:
            final_message = render_template(template.message, context)
        else:
            title_val = context.get("task_title") or context.get("quotation_number") or context.get("role_name") or ""
            if title_val:
                final_message = f"Notification ({event_type}): {title_val}"
            else:
                final_message = f"Notification for event {event_type}."

        # 3. Determine channel
        final_channel = channel
        if not final_channel:
            if template:
                final_channel = template.channel
            else:
                final_channel = NotificationChannel.IN_APP

        created_notifications = []

        for user in recipients:
            try:
                # Build user-specific context overrides if user attributes missing
                user_ctx = dict(context)
                if "user_name" not in user_ctx:
                    user_ctx["user_name"] = user.get_full_name() or user.username
                if "employee_name" not in user_ctx:
                    user_ctx["employee_name"] = user.get_full_name() or user.username

                user_message = render_template(final_message, user_ctx)

                notification = Notification.objects.create(
                    recipient=user,
                    template=template,
                    event_type=event_type,
                    message=user_message,
                    channel=final_channel,
                    is_read=False,
                )

                # 4. Handle EMAIL / BOTH channels
                if final_channel in (NotificationChannel.EMAIL, NotificationChannel.BOTH):
                    send_notification_email(user, event_type, user_message)

                created_notifications.append(notification)
            except Exception as e:
                logger.error(
                    "Failed to create notification for user '%s' (event='%s'): %s",
                    getattr(user, "username", user), event_type, e,
                )

        return created_notifications

    except Exception as e:
        logger.error(
            "Unexpected error in trigger_notification_event (event='%s'): %s",
            event_type, e,
        )
        return []


def send_notification_email(recipient, subject, message):
    """Utility to send an email notification."""
    if not recipient or not recipient.email:
        logger.warning("Cannot send email: Recipient has no email address.")
        return False

    try:
        send_mail(
            subject=f"CRM Notification: {subject}",
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@crm.local"),
            recipient_list=[recipient.email.strip()],
            fail_silently=True,
        )
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", recipient.email, e)
        return False


# Backwards compatibility alias for code calling create_notification
def create_notification(user, title, message, type_name="System", template=None, scheduled_at=None, edited_by=None, is_customized=False):
    """Backward compatibility function wrapping trigger_notification_event."""
    try:
        results = trigger_notification_event(
            event_type=type_name,
            recipient=user,
            custom_message=message,
            template_id=template.pk if template else None,
        )
        return results[0] if results else None
    except Exception as e:
        logger.error("Failed to create notification (type='%s'): %s", type_name, e)
        return None
