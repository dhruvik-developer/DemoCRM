from celery import shared_task
from Task.services import process_due_task_reminders, process_due_meeting_reminders
import logging

logger = logging.getLogger(__name__)

@shared_task
def task_due_reminder_job():
    """
    Celery task jo roz subah pending tasks ke reminders bhejta hai.
    """
    logger.info("Celery Job Started: Checking for due tasks...")
    count = process_due_task_reminders()
    logger.info(f"Celery Job Finished: Sent {count} task reminders.")
    return f"Processed {count} task reminders."


@shared_task
def meeting_reminder_job():
    """
    Celery task jo har 5 minute mein 15-min-before meeting alerts bhejta hai.
    """
    count = process_due_meeting_reminders()
    return f"Processed {count} meeting reminders."