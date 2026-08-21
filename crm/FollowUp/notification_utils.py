"""
Shared helpers for:
  1. Creating an in-system Notification row for a user.
  2. Sending a plain reminder/notification email.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification, NotificationTemplate, NotificationType

logger = logging.getLogger(__name__)


def create_notification(user, title, message, type_name="System"):
    if user is None:
        return None

    notification_type, _ = NotificationType.objects.get_or_create(type_name=type_name)

    template, _ = NotificationTemplate.objects.get_or_create(
        subject=title,
        defaults={"body": message},
    )

    return Notification.objects.create(
        user_id=user,
        notification_type_id=notification_type,
        template_id=template,
        title=title,
        message=message,
    )


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
