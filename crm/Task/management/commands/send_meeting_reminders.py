from django.core.management.base import BaseCommand
from Task.services import process_due_meeting_reminders


class Command(BaseCommand):
    help = "Process pending 15-minute-before meeting reminders and send emails to host and lead."

    def handle(self, *args, **options):
        sent_count = process_due_meeting_reminders()
        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed {sent_count} meeting reminders.")
        )
