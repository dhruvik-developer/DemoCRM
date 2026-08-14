from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Reminder, ReminderType, ReminderStatus
from FollowUp.notification_utils import create_notification


# ======================================================
# EMAIL: SEND MEETING EMAIL TO LEAD
# ======================================================

def send_lead_meeting_reminder_email(meeting):
    """
    Send meeting creation email to the Lead.
    """
    lead = getattr(meeting, "lead", None)
    if not lead:
        return False

    lead_email = getattr(lead, "email", None)
    if not lead_email:
        return False

    lead_email = lead_email.strip()
    if not lead_email:
        return False

    lead_name = getattr(lead, "name", "") or "Valued Client"
    meeting_title = getattr(meeting, "meeting_title", "Meeting")
    meeting_date = getattr(meeting, "meeting_date", "")
    start_time = getattr(meeting, "start_time", "")
    end_time = getattr(meeting, "end_time", "")
    location = getattr(meeting, "location", "") or "Online / Office"
    description = getattr(meeting, "description", "") or "N/A"

    subject = f"Meeting Scheduled: {meeting_title}"
    message = (
        f"Hello {lead_name},\n\n"
        f"A meeting has been scheduled with you.\n\n"
        f"Meeting Title: {meeting_title}\n"
        f"Date: {meeting_date}\n"
        f"Time: {start_time} - {end_time}\n"
        f"Location: {location}\n"
        f"Description: {description}\n\n"
        f"Please be ready at the scheduled time.\n\n"
        f"Best regards,\n"
        f"CRM Team"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[lead_email],
        fail_silently=False,
    )
    return True


# ======================================================
# EMAIL: SEND MEETING EMAIL TO EMPLOYEE / CREATOR
# ======================================================

def send_meeting_reminder_email(
    meeting,
    recipient_email,
    recipient_name=None,
):
    """
    Send meeting email to an employee/creator/assigned user.
    """
    if not recipient_email:
        return False

    recipient_email = recipient_email.strip()
    if not recipient_email:
        return False

    recipient_name = recipient_name or "User"
    meeting_title = getattr(meeting, "meeting_title", "Meeting")
    meeting_date = getattr(meeting, "meeting_date", "")
    start_time = getattr(meeting, "start_time", "")
    end_time = getattr(meeting, "end_time", "")
    location = getattr(meeting, "location", "") or "Online / Office"
    lead_name = getattr(meeting.lead, "name", "N/A") if getattr(meeting, "lead", None) else "N/A"

    subject = f"Meeting Confirmation: {meeting_title}"
    message = (
        f"Hello {recipient_name},\n\n"
        f"Your meeting has been scheduled successfully.\n\n"
        f"Meeting Title: {meeting_title}\n"
        f"Lead / Client: {lead_name}\n"
        f"Date: {meeting_date}\n"
        f"Time: {start_time} - {end_time}\n"
        f"Location: {location}\n\n"
        f"Best regards,\n"
        f"CRM System"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
        fail_silently=False,
    )
    return True


# ======================================================
# REMINDER: CREATE MEETING REMINDER (DATABASE)
# ======================================================

def create_meeting_reminder(
    meeting,
    reminder_for,
    minutes_before=15,
):
    """
    Create a database reminder in the Reminder table.
    """
    if not meeting or not reminder_for:
        return None

    meeting_date = getattr(meeting, "meeting_date", None)
    start_time = getattr(meeting, "start_time", None)
    if not meeting_date or not start_time:
        return None

    meeting_datetime = timezone.make_aware(
        datetime.combine(meeting_date, start_time)
    )
    reminder_datetime = meeting_datetime - timedelta(minutes=minutes_before)

    reminder_type, _ = ReminderType.objects.get_or_create(
        type_name="Meeting Reminder",
        defaults={"is_active": True}
    )
    reminder_status, _ = ReminderStatus.objects.get_or_create(
        status_name="Pending",
        defaults={"is_active": True}
    )

    reminder = Reminder.objects.create(
        task_id=getattr(meeting, "task_id", None),
        meeting_id=meeting,
        reminder_for=reminder_for,
        reminder_type_id=reminder_type,
        reminder_status_id=reminder_status,
        reminder_datetime=reminder_datetime,
        message=(
            f"Reminder: {meeting.meeting_title} "
            f"is scheduled at {start_time}."
        ),
        created_by=meeting.created_by,
        is_sent=False,
    )
    return reminder


# ======================================================
# MEETING CREATION: EMAILS + IN-SYSTEM NOTIFICATIONS
# ======================================================

def send_meeting_creation_emails(meeting):
    """
    Called after a Meeting is successfully created:
    1. Sends confirmation email to Lead.
    2. Sends confirmation email to Creator/Host.
    3. Creates In-System Notification in the CRM notification bell.
    4. Creates 15-minute pre-meeting Reminder in database.
    """
    lead_name = getattr(meeting.lead, "name", "Client") if getattr(meeting, "lead", None) else "Client"

    # 1. Send Email to Lead
    try:
        send_lead_meeting_reminder_email(meeting)
    except Exception as e:
        print(f"Error sending email to lead: {e}")

    # 2. Send Email to Creator / Host
    if meeting.created_by and getattr(meeting.created_by, "email", None):
        try:
            send_meeting_reminder_email(
                meeting=meeting,
                recipient_email=meeting.created_by.email,
                recipient_name=meeting.created_by.username,
            )
        except Exception as e:
            print(f"Error sending email to creator: {e}")

    # 3. Create In-System Notification for Creator
    if meeting.created_by:
        try:
            create_notification(
                user=meeting.created_by,
                title=f"New Meeting: {meeting.meeting_title}",
                message=(
                    f"Meeting '{meeting.meeting_title}' is scheduled with {lead_name} "
                    f"on {meeting.meeting_date} at {meeting.start_time}."
                ),
                type_name="Meeting"
            )
        except Exception as e:
            print(f"Error creating in-system notification: {e}")

    # 4. Create in-system Notification for Assigned Employee (if different)
    if meeting.task_id and meeting.task_id.assigned_to and meeting.task_id.assigned_to != meeting.created_by:
        try:
            create_notification(
                user=meeting.task_id.assigned_to,
                title=f"Meeting Scheduled: {meeting.meeting_title}",
                message=(
                    f"Meeting '{meeting.meeting_title}' is scheduled on your task with {lead_name} "
                    f"on {meeting.meeting_date} at {meeting.start_time}."
                ),
                type_name="Meeting"
            )
        except Exception as e:
            print(f"Error creating notification for assigned employee: {e}")

    # 5. Create Database Reminder (for 15-min background check)
    if meeting.created_by:
        try:
            create_meeting_reminder(
                meeting=meeting,
                reminder_for=meeting.created_by,
                minutes_before=15,
            )
        except Exception as e:
            print(f"Error creating database reminder: {e}")

    return True


# ======================================================
# DUE REMINDER BACKGROUND WORKER (15-MIN BEFORE)
# ======================================================

def send_due_reminder_notification(reminder):
    """
    Sends the 15-minute-before email and in-system notification when due.
    """
    meeting = reminder.meeting_id
    if not meeting:
        return

    # In-System Notification
    if reminder.reminder_for:
        create_notification(
            user=reminder.reminder_for,
            title=f"Meeting Starting in 15 Mins: {meeting.meeting_title}",
            message=f"Your meeting '{meeting.meeting_title}' will start at {meeting.start_time}.",
            type_name="Meeting Reminder"
        )

    # Email to Host
    if reminder.reminder_for and getattr(reminder.reminder_for, "email", None):
        send_mail(
            subject=f"Meeting Starting in 15 Minutes - {meeting.meeting_title}",
            message=f"Hello,\n\nYour meeting '{meeting.meeting_title}' will start in 15 minutes at {meeting.start_time}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reminder.reminder_for.email],
            fail_silently=True,
        )

    # Email to Lead
    if meeting.lead and getattr(meeting.lead, "email", None):
        send_mail(
            subject=f"Meeting Starting in 15 Minutes - {meeting.meeting_title}",
            message=f"Hello {getattr(meeting.lead, 'name', '')},\n\nYour meeting '{meeting.meeting_title}' will start in 15 minutes at {meeting.start_time}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[meeting.lead.email],
            fail_silently=True,
        )


def process_due_meeting_reminders():
    """
    Finds all pending reminders where reminder_datetime <= now and is_sent=False,
    triggers notification and marks is_sent=True.
    """
    now = timezone.now()
    due_reminders = Reminder.objects.filter(
        is_sent=False,
        reminder_datetime__lte=now,
    ).select_related("meeting_id", "meeting_id__lead", "reminder_for")

    sent_count = 0
    for reminder in due_reminders:
        send_due_reminder_notification(reminder)
        reminder.is_sent = True
        reminder.save(update_fields=["is_sent"])
        sent_count += 1

    return sent_count