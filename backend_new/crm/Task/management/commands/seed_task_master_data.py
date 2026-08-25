from django.core.management.base import BaseCommand
from Task.services import seed_task_master_data


class Command(BaseCommand):
    help = "Seed canonical Task master data (Status, Priority, Category)."

    def handle(self, *args, **options):
        result = seed_task_master_data()
        self.stdout.write(
            self.style.SUCCESS(f"Task master data seeded successfully: {result}")
        )
