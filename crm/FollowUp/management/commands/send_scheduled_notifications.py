"""
Send pending email notifications that have not yet been sent.

Run periodically via cron / Task Scheduler / Celery beat:

    python manage.py send_scheduled_notifications
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from Notification.models import Notification, NotificationChannel
from Notification.notification_utils import send_notification_email


class Command(BaseCommand):

    help = "Send pending email notifications that have not yet been emailed."

    def handle(self, *args, **options):

        due = Notification.objects.filter(
            channel__in=[NotificationChannel.EMAIL, NotificationChannel.BOTH],
            is_read=False,
            created_at__lte=timezone.now(),
        )

        count = 0

        for notification in due:
            if send_notification_email(notification.recipient, notification.event_type, notification.message):
                count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Sent {count} pending notification(s).")
        )
