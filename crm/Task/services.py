import logging
from datetime import datetime, timedelta

from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import (
    Meeting,
    Reminder,
    ReminderStatus,
    ReminderType,
)

from FollowUp.notification_utils import create_notification


logger = logging.getLogger(__name__)


# ======================================================
# EMAIL: SEND MEETING EMAIL TO LEAD
# ======================================================

def send_lead_meeting_reminder_email(meeting):
    """
    Send meeting creation email to the Lead.
    """

    try:
        lead = getattr(meeting, "lead", None)

        if not lead:
            logger.warning(
                "Cannot send lead meeting email: lead missing "
                "meeting_id=%s",
                getattr(meeting, "meeting_id", None),
            )
            return False

        lead_email = getattr(lead, "email", None)

        if not lead_email:
            logger.warning(
                "Cannot send lead meeting email: lead email missing "
                "meeting_id=%s",
                getattr(meeting, "meeting_id", None),
            )
            return False

        lead_email = lead_email.strip()

        if not lead_email:
            logger.warning(
                "Cannot send lead meeting email: empty email "
                "meeting_id=%s",
                getattr(meeting, "meeting_id", None),
            )
            return False

        lead_name = getattr(
            lead,
            "name",
            "",
        ) or "Valued Client"

        meeting_title = getattr(
            meeting,
            "meeting_title",
            "Meeting",
        )

        meeting_date = getattr(
            meeting,
            "meeting_date",
            "",
        )

        start_time = getattr(
            meeting,
            "start_time",
            "",
        )

        end_time = getattr(
            meeting,
            "end_time",
            "",
        )

        location = getattr(
            meeting,
            "location",
            "",
        ) or "Online / Office"

        description = getattr(
            meeting,
            "description",
            "",
        ) or "N/A"

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

        logger.info(
            "Meeting email sent to lead: meeting_id=%s recipient=%s",
            getattr(meeting, "meeting_id", None),
            lead_email,
        )

        return True

    except Exception:
        logger.exception(
            "Error sending meeting email to lead: meeting_id=%s",
            getattr(meeting, "meeting_id", None),
        )
        return False


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

    try:
        if not recipient_email:
            logger.warning(
                "Cannot send meeting email: recipient email missing "
                "meeting_id=%s",
                getattr(meeting, "meeting_id", None),
            )
            return False

        recipient_email = recipient_email.strip()

        if not recipient_email:
            logger.warning(
                "Cannot send meeting email: empty recipient email "
                "meeting_id=%s",
                getattr(meeting, "meeting_id", None),
            )
            return False

        recipient_name = recipient_name or "User"

        meeting_title = getattr(
            meeting,
            "meeting_title",
            "Meeting",
        )

        meeting_date = getattr(
            meeting,
            "meeting_date",
            "",
        )

        start_time = getattr(
            meeting,
            "start_time",
            "",
        )

        end_time = getattr(
            meeting,
            "end_time",
            "",
        )

        location = getattr(
            meeting,
            "location",
            "",
        ) or "Online / Office"

        lead_name = (
            getattr(meeting.lead, "name", "N/A")
            if getattr(meeting, "lead", None)
            else "N/A"
        )

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

        logger.info(
            "Meeting email sent successfully: meeting_id=%s recipient=%s",
            getattr(meeting, "meeting_id", None),
            recipient_email,
        )

        return True

    except Exception:
        logger.exception(
            "Error sending meeting email: meeting_id=%s recipient=%s",
            getattr(meeting, "meeting_id", None),
            recipient_email,
        )
        return False


# ======================================================
# REMINDER: CREATE MEETING REMINDER
# ======================================================

def create_meeting_reminder(
    meeting,
    reminder_for,
    minutes_before=15,
):
    """
    Create a database reminder in the Reminder table.
    """

    try:
        if not meeting or not reminder_for:
            logger.warning(
                "Meeting reminder not created: "
                "meeting or reminder_for missing."
            )
            return None

        meeting_date = getattr(
            meeting,
            "meeting_date",
            None,
        )

        start_time = getattr(
            meeting,
            "start_time",
            None,
        )

        if not meeting_date or not start_time:
            logger.warning(
                "Meeting reminder not created: date/time missing "
                "meeting_id=%s",
                getattr(meeting, "meeting_id", None),
            )
            return None

        meeting_datetime = timezone.make_aware(
            datetime.combine(
                meeting_date,
                start_time,
            )
        )

        reminder_datetime = (
            meeting_datetime
            - timedelta(minutes=minutes_before)
        )

        reminder_type, _ = ReminderType.objects.get_or_create(
            type_name="Meeting Reminder",
            defaults={"is_active": True},
        )

        reminder_status, _ = ReminderStatus.objects.get_or_create(
            status_name="Pending",
            defaults={"is_active": True},
        )

        reminder = Reminder.objects.create(
            task_id=getattr(
                meeting,
                "task_id",
                None,
            ),
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

        logger.info(
            "Meeting reminder created: "
            "reminder_id=%s meeting_id=%s reminder_for=%s "
            "reminder_datetime=%s",
            reminder.reminder_id,
            getattr(meeting, "meeting_id", None),
            getattr(reminder_for, "pk", None),
            reminder.reminder_datetime,
        )

        return reminder

    except Exception:
        logger.exception(
            "Error creating meeting reminder: meeting_id=%s",
            getattr(meeting, "meeting_id", None),
        )
        return None


# ======================================================
# MEETING DATABASE WORKFLOW
# ======================================================

def create_meeting_database_records(meeting):
    """
    Create all database records related to a meeting
    in one atomic transaction.

    Database records:
    1. Creator notification
    2. Assigned employee notification
    3. 15-minute reminder
    """

    lead_name = (
        getattr(meeting.lead, "name", "Client")
        if getattr(meeting, "lead", None)
        else "Client"
    )

    with transaction.atomic():

        # --------------------------------------------------
        # 1. CREATOR NOTIFICATION
        # --------------------------------------------------

        if meeting.created_by:

            create_notification(
                user=meeting.created_by,
                title=f"New Meeting: {meeting.meeting_title}",
                message=(
                    f"Meeting '{meeting.meeting_title}' "
                    f"is scheduled with {lead_name} "
                    f"on {meeting.meeting_date} "
                    f"at {meeting.start_time}."
                ),
                type_name="Meeting",
            )

        # --------------------------------------------------
        # 2. ASSIGNED EMPLOYEE NOTIFICATION
        # --------------------------------------------------

        if (
            meeting.task_id
            and meeting.task_id.assigned_to
            and meeting.task_id.assigned_to != meeting.created_by
        ):

            assigned_user = meeting.task_id.assigned_to

            create_notification(
                user=assigned_user,
                title=f"Meeting Scheduled: {meeting.meeting_title}",
                message=(
                    f"Meeting '{meeting.meeting_title}' "
                    f"is scheduled on your task with {lead_name} "
                    f"on {meeting.meeting_date} "
                    f"at {meeting.start_time}."
                ),
                type_name="Meeting",
            )

        # --------------------------------------------------
        # 3. DATABASE REMINDER
        # --------------------------------------------------

        reminder = None

        if meeting.created_by:

            reminder = create_meeting_reminder(
                meeting=meeting,
                reminder_for=meeting.created_by,
                minutes_before=15,
            )

            if reminder is None:
                raise ValueError(
                    "Failed to create meeting reminder."
                )

        logger.info(
            "Meeting database records created successfully: "
            "meeting_id=%s reminder_id=%s",
            meeting.meeting_id,
            getattr(reminder, "reminder_id", None),
        )

        return reminder


# ======================================================
# MEETING CREATION: EMAILS + DATABASE WORKFLOW
# ======================================================

def send_meeting_creation_emails(meeting):
    """
    Called after a Meeting is successfully created.

    1. Sends confirmation email to Lead.
    2. Sends confirmation email to Creator/Host.
    3. Creates database notifications and reminder
       inside one atomic transaction.
    """

    try:

        # ==================================================
        # 1. EMAIL TO LEAD
        # ==================================================

        try:
            send_lead_meeting_reminder_email(
                meeting
            )

        except Exception:
            logger.exception(
                "Error sending email to lead: "
                "meeting_id=%s",
                getattr(
                    meeting,
                    "meeting_id",
                    None,
                ),
            )

        # ==================================================
        # 2. EMAIL TO CREATOR / HOST
        # ==================================================

        if (
            meeting.created_by
            and getattr(
                meeting.created_by,
                "email",
                None,
            )
        ):

            try:

                send_meeting_reminder_email(
                    meeting=meeting,
                    recipient_email=meeting.created_by.email,
                    recipient_name=meeting.created_by.username,
                )

            except Exception:
                logger.exception(
                    "Error sending creator email: "
                    "meeting_id=%s user_id=%s",
                    getattr(
                        meeting,
                        "meeting_id",
                        None,
                    ),
                    getattr(
                        meeting.created_by,
                        "pk",
                        None,
                    ),
                )

        # ==================================================
        # 3. DATABASE TRANSACTION
        # ==================================================

        try:

            reminder = create_meeting_database_records(
                meeting
            )

            logger.info(
                "Meeting database workflow completed: "
                "meeting_id=%s reminder_id=%s",
                meeting.meeting_id,
                getattr(
                    reminder,
                    "reminder_id",
                    None,
                ),
            )

        except Exception:

            logger.exception(
                "Meeting database workflow failed: "
                "meeting_id=%s",
                meeting.meeting_id,
            )

            raise

        # ==================================================
        # WORKFLOW COMPLETED
        # ==================================================

        logger.info(
            "Meeting creation workflow completed: "
            "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return True

    except Exception:

        logger.exception(
            "Unexpected error in meeting creation workflow: "
            "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return False


# ======================================================
# DUE REMINDER: SEND EMAIL + NOTIFICATION
# ======================================================

def send_due_reminder_notification(reminder):
    """
    Sends the 15-minute-before email and
    in-system notification when due.
    """

    try:

        meeting = reminder.meeting_id

        if not meeting:

            logger.warning(
                "Due reminder skipped: meeting missing "
                "reminder_id=%s",
                reminder.reminder_id,
            )

            return False

        # --------------------------------------------------
        # IN-SYSTEM NOTIFICATION
        # --------------------------------------------------

        if reminder.reminder_for:

            create_notification(
                user=reminder.reminder_for,
                title=(
                    f"Meeting Starting in 15 Mins: "
                    f"{meeting.meeting_title}"
                ),
                message=(
                    f"Your meeting '{meeting.meeting_title}' "
                    f"will start at {meeting.start_time}."
                ),
                type_name="Meeting Reminder",
            )

            logger.info(
                "Reminder notification created: "
                "reminder_id=%s user_id=%s",
                reminder.reminder_id,
                getattr(
                    reminder.reminder_for,
                    "pk",
                    None,
                ),
            )

        # --------------------------------------------------
        # EMAIL TO HOST
        # --------------------------------------------------

        if (
            reminder.reminder_for
            and getattr(
                reminder.reminder_for,
                "email",
                None,
            )
        ):

            send_mail(
                subject=(
                    f"Meeting Starting in 15 Minutes - "
                    f"{meeting.meeting_title}"
                ),
                message=(
                    f"Hello,\n\n"
                    f"Your meeting '{meeting.meeting_title}' "
                    f"will start in 15 minutes "
                    f"at {meeting.start_time}."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[
                    reminder.reminder_for.email
                ],
                fail_silently=False,
            )

            logger.info(
                "Due reminder email sent to host: "
                "reminder_id=%s recipient=%s",
                reminder.reminder_id,
                reminder.reminder_for.email,
            )

        # --------------------------------------------------
        # EMAIL TO LEAD
        # --------------------------------------------------

        if (
            meeting.lead
            and getattr(
                meeting.lead,
                "email",
                None,
            )
        ):

            send_mail(
                subject=(
                    f"Meeting Starting in 15 Minutes - "
                    f"{meeting.meeting_title}"
                ),
                message=(
                    f"Hello "
                    f"{getattr(meeting.lead, 'name', '')},\n\n"
                    f"Your meeting '{meeting.meeting_title}' "
                    f"will start in 15 minutes "
                    f"at {meeting.start_time}."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[
                    meeting.lead.email
                ],
                fail_silently=False,
            )

            logger.info(
                "Due reminder email sent to lead: "
                "reminder_id=%s recipient=%s",
                reminder.reminder_id,
                meeting.lead.email,
            )

        return True

    except Exception:

        logger.exception(
            "Error sending due reminder: reminder_id=%s",
            getattr(
                reminder,
                "reminder_id",
                None,
            ),
        )

        return False


# ======================================================
# PROCESS DUE MEETING REMINDERS
# ======================================================

def process_due_meeting_reminders():
    """
    Finds all pending reminders where:
        reminder_datetime <= now
        is_sent=False

    Sends notification/email and marks reminder as sent.
    """

    try:

        now = timezone.now()

        due_reminders = (
            Reminder.objects
            .filter(
                is_sent=False,
                reminder_datetime__lte=now,
            )
            .select_related(
                "meeting_id",
                "meeting_id__lead",
                "reminder_for",
            )
        )

        sent_count = 0

        for reminder in due_reminders:

            try:

                success = send_due_reminder_notification(
                    reminder
                )

                if success:

                    reminder.is_sent = True

                    reminder.save(
                        update_fields=["is_sent"]
                    )

                    sent_count += 1

                    logger.info(
                        "Due meeting reminder processed successfully: "
                        "reminder_id=%s",
                        reminder.reminder_id,
                    )

                else:

                    logger.warning(
                        "Due meeting reminder was not sent: "
                        "reminder_id=%s",
                        reminder.reminder_id,
                    )

            except Exception:

                logger.exception(
                    "Error processing due meeting reminder: "
                    "reminder_id=%s",
                    reminder.reminder_id,
                )

        logger.info(
            "Due meeting reminder processing completed: "
            "sent_count=%s",
            sent_count,
        )

        return sent_count

    except Exception:

        logger.exception(
            "Unexpected error while processing "
            "due meeting reminders."
        )

        return 0