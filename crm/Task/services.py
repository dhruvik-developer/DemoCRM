from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Reminder, ReminderType, ReminderStatus


def send_meeting_reminder_email(meeting, recipient_email, recipient_name=""):
    """
    Send a generic meeting reminder email to a single recipient.
    """
    if not recipient_email:
        return False

    greeting = f"Hello {recipient_name},\n\n" if recipient_name else "Hello,\n\n"
    subject = f"Meeting Scheduled - {meeting.meeting_title}"
    message = (
        f"{greeting}"
        f"This is a confirmation for your scheduled meeting.\n\n"
        f"Meeting Title: {meeting.meeting_title}\n"
        f"Date: {meeting.meeting_date}\n"
        f"Start Time: {meeting.start_time}\n"
        f"End Time: {meeting.end_time}\n"
        f"Location: {meeting.location or 'Not specified'}\n"
        f"Description: {meeting.description or 'No description'}\n\n"
        f"Please be ready for the meeting.\n\n"
        f"Thank you."
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@democrm.local")
    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[recipient_email],
        fail_silently=True,
    )
    return True


def create_meeting_reminder(
    meeting,
    reminder_for,
    reminder_type=None,
    reminder_status=None,
    minutes_before=15,
    created_by=None,
):
    """
    Create a Reminder entry in the database for an employee/user.
    """
    if not reminder_for:
        return None

    meeting_datetime = timezone.make_aware(
        datetime.combine(
            meeting.meeting_date,
            meeting.start_time
        )
    )
    reminder_datetime = (
        meeting_datetime - timedelta(minutes=minutes_before)
    )

    if not reminder_type:
        reminder_type = ReminderType.objects.filter(is_active=True).first()
    if not reminder_status:
        reminder_status = ReminderStatus.objects.filter(is_active=True).first()

    if not reminder_type or not reminder_status:
        return None

    reminder = Reminder.objects.create(
        task_id=meeting.task_id,
        meeting_id=meeting,
        reminder_for=reminder_for,
        reminder_type_id=reminder_type,
        reminder_status_id=reminder_status,
        reminder_datetime=reminder_datetime,
        message=(
            f"Reminder: {meeting.meeting_title} "
            f"is scheduled at {meeting.start_time}."
        ),
        created_by=created_by or meeting.created_by,
    )

    return reminder


def create_employee_meeting_reminder(
    meeting,
    reminder_type=None,
    reminder_status=None,
    minutes_before=15,
):
    """
    Create meeting reminder for the employee assigned to the task.
    """
    employee = meeting.task_id.assigned_to if meeting.task_id else None
    if not employee:
        return None

    return create_meeting_reminder(
        meeting=meeting,
        reminder_for=employee,
        reminder_type=reminder_type,
        reminder_status=reminder_status,
        minutes_before=minutes_before,
        created_by=meeting.created_by,
    )


def get_lead_email(meeting):
    """
    Get email address from the Lead.
    """
    if not meeting.lead:
        return None

    return getattr(meeting.lead, "email", None)


def send_lead_meeting_reminder_email(meeting):
    """
    Send meeting email to the Lead.
    """
    lead_email = get_lead_email(meeting)
    if not lead_email:
        return False

    lead_name = getattr(meeting.lead, "name", "")
    return send_meeting_reminder_email(
        meeting=meeting,
        recipient_email=lead_email,
        recipient_name=lead_name,
    )


def send_meeting_creation_emails(meeting):
    """
    Sends emails to both the Lead and the Meeting Creator / Assigned Employee,
    and creates a pre-meeting Reminder entry in the database.
    """
    # 1. Send Email to Lead (if meeting has a lead with email)
    send_lead_meeting_reminder_email(meeting)

    # 2. Send Email to Meeting Creator
    if meeting.created_by and getattr(meeting.created_by, "email", None):
        send_meeting_reminder_email(
            meeting=meeting,
            recipient_email=meeting.created_by.email,
            recipient_name=meeting.created_by.username,
        )

    # 3. Send Email to Assigned Employee if different from creator
    if meeting.task_id and meeting.task_id.assigned_to:
        assigned_user = meeting.task_id.assigned_to
        if assigned_user != meeting.created_by and getattr(assigned_user, "email", None):
            send_meeting_reminder_email(
                meeting=meeting,
                recipient_email=assigned_user.email,
                recipient_name=assigned_user.username,
            )

    # 4. Create in-database pre-meeting reminder (15 mins before) for creator/assigned employee
    try:
        if meeting.created_by:
            create_meeting_reminder(
                meeting=meeting,
                reminder_for=meeting.created_by,
                minutes_before=15,
            )
    except Exception:
        pass


def send_due_reminder_notification(reminder):
    """
    Sends the 15-minute-before reminder email when a reminder is due.
    """
    meeting = reminder.meeting_id
    if not meeting:
        return

    subject = f"Upcoming Meeting Reminder (in 15 mins) - {meeting.meeting_title}"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@democrm.local")

    # 1. Send to Employee / Host
    if reminder.reminder_for and getattr(reminder.reminder_for, "email", None):
        msg = (
            f"Hello {reminder.reminder_for.username},\n\n"
            f"This is a reminder that your meeting '{meeting.meeting_title}' is scheduled to start in 15 minutes.\n\n"
            f"Meeting Title: {meeting.meeting_title}\n"
            f"Date: {meeting.meeting_date}\n"
            f"Time: {meeting.start_time} - {meeting.end_time}\n"
            f"Location: {meeting.location or 'Not specified'}\n"
            f"Lead: {meeting.lead.name if meeting.lead else 'N/A'}\n\n"
            f"Please be ready.\n\n"
            f"Thank you,\nCRM System"
        )
        send_mail(
            subject=subject,
            message=msg,
            from_email=from_email,
            recipient_list=[reminder.reminder_for.email],
            fail_silently=True,
        )

    # 2. Send to Lead if attached to meeting
    if meeting.lead and getattr(meeting.lead, "email", None):
        lead_msg = (
            f"Hello {meeting.lead.name},\n\n"
            f"This is a quick reminder that your meeting '{meeting.meeting_title}' will begin in 15 minutes.\n\n"
            f"Meeting Title: {meeting.meeting_title}\n"
            f"Date: {meeting.meeting_date}\n"
            f"Time: {meeting.start_time} - {meeting.end_time}\n"
            f"Location: {meeting.location or 'Online / Office'}\n\n"
            f"We look forward to speaking with you!\n\n"
            f"Best regards,\nCRM Team"
        )
        send_mail(
            subject=subject,
            message=lead_msg,
            from_email=from_email,
            recipient_list=[meeting.lead.email],
            fail_silently=True,
        )


def process_due_meeting_reminders():
    """
    Finds all pending reminders where reminder_datetime <= now and is_sent=False,
    sends the 15-min-before email to both employee and lead, and marks them as sent.
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
