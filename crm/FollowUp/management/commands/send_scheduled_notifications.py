"""
Send scheduled notifications whose scheduled_at has passed.

Run periodically via cron / Task Scheduler / Celery beat:

    python manage.py send_scheduled_notifications
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from FollowUp.models import Notification
from FollowUp.notification_utils import send_notification_email


class Command(BaseCommand):

    help = "Send scheduled notifications whose scheduled_at has passed."

    def handle(self, *args, **options):

        due = Notification.objects.filter(
            status=Notification.Status.SCHEDULED,
            scheduled_at__lte=timezone.now(),
        )

        count = 0

        for notification in due:
            if send_notification_email(notification):
                count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Sent {count} scheduled notification(s).")
        )
