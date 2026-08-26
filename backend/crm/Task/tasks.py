import logging

import pytz
from celery import shared_task

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import Meeting

from .services import (
    process_due_task_reminders,
    send_meeting_scheduled_emails,
    send_meeting_5_minute_reminder,
    generate_google_meet_link,
    ONLINE_MEETING_TYPE_ID,
    OFFLINE_MEETING_TYPE_ID,
    OFFICE_LOCATION,
)

from Notification.notification_utils import (
    create_notification,
    trigger_notification_event,
)


logger = logging.getLogger(__name__)


# ======================================================
# EXISTING TASK REMINDER
# ======================================================


@shared_task
def task_due_reminder_job():

    logger.info("Celery Job Started: Checking for due tasks...")

    count = process_due_task_reminders()

    logger.info(
        "Celery Job Finished: Sent %s task reminders.",
        count,
    )

    return f"Processed {count} task reminders."


# ======================================================
# MEETING REMINDER JOB
# ======================================================


@shared_task
def meeting_reminder_job():

    tz = pytz.timezone(settings.CELERY_TIMEZONE)
    now = timezone.now().astimezone(tz)
    today = now.date()

    # Query meetings starting within the next ~5-6 minutes
    window_start = now
    window_end = now + timezone.timedelta(minutes=5, seconds=59)

    meetings = Meeting.objects.filter(
        approval_status=Meeting.ApprovalStatus.APPROVED,
        reminder_sent_at__isnull=True,
        meeting_date=today,
        start_time__gte=window_start.time(),
        start_time__lte=window_end.time(),
    ).select_related(
        "created_by",
        "manager",
        "lead",
        "meeting_type_id",
    )

    sent_count = 0

    for meeting in meetings:

        try:

            # Safety check
            if meeting.approval_status != Meeting.ApprovalStatus.APPROVED:
                continue

            success = send_meeting_5_minute_reminder(meeting)

            if success:

                meeting.reminder_sent_at = timezone.now()

                meeting.save(
                    update_fields=[
                        "reminder_sent_at",
                        "updated_at",
                    ]
                )

                # ==========================================
                # EMPLOYEE IN-APP NOTIFICATION
                # ==========================================

                if meeting.created_by:

                    create_notification(
                        user=meeting.created_by,
                        title=(f"Meeting Reminder: " f"{meeting.meeting_title}"),
                        message=(
                            f"Meeting starts in 5 minutes " f"at {meeting.start_time}."
                        ),
                        type_name="Meeting Reminder",
                    )

                # ==========================================
                # MANAGER IN-APP NOTIFICATION
                # ==========================================

                if meeting.manager:

                    create_notification(
                        user=meeting.manager,
                        title=(f"Meeting Reminder: " f"{meeting.meeting_title}"),
                        message=(
                            f"Meeting starts in 5 minutes " f"at {meeting.start_time}."
                        ),
                        type_name="Meeting Reminder",
                    )

                sent_count += 1

                logger.info(
                    "5-minute reminder processed: " "meeting_id=%s",
                    meeting.meeting_id,
                )

        except Exception:

            logger.exception(
                "Meeting reminder failed: meeting_id=%s",
                meeting.meeting_id,
            )

    return f"Processed {sent_count} meeting reminders."


# ======================================================
# MANAGER APPROVAL REQUEST
# ======================================================


@shared_task
def notify_manager_about_meeting(meeting_id, template_id=None):

    try:

        meeting = Meeting.objects.select_related(
            "manager",
            "created_by",
            "lead",
            "meeting_type_id",
        ).get(meeting_id=meeting_id)

        # Safety
        if meeting.approval_status != Meeting.ApprovalStatus.PENDING:
            return False

        manager = meeting.manager

        if not manager:
            return False

        # ==================================================
        # MEETING TYPE CHECK
        # ==================================================

        m_type_id = None
        m_type_name = ""
        if meeting.meeting_type_id:
            m_type_id = getattr(meeting.meeting_type_id, "meeting_type_id", None)
            m_type_name = (
                getattr(meeting.meeting_type_id, "type_name", "") or ""
            ).lower()

        is_online = (m_type_id == ONLINE_MEETING_TYPE_ID) or ("online" in m_type_name)
        is_offline = (m_type_id == OFFLINE_MEETING_TYPE_ID) or (
            "offline" in m_type_name
        )

        # ==================================================
        # ONLINE: Auto generate Google Meet link
        # ==================================================

        if is_online:

            if not meeting.meeting_link:
                meet_link = generate_google_meet_link(meeting)
                if meet_link:
                    meeting.meeting_link = meet_link
                    meeting.save(
                        update_fields=[
                            "meeting_link",
                            "updated_at",
                        ]
                    )

            event_type = "ONLINE_MEETING_CREATED"

        # ==================================================
        # OFFLINE: Set office location
        # ==================================================

        elif is_offline:

            if not meeting.location:
                meeting.location = OFFICE_LOCATION
                meeting.save(
                    update_fields=[
                        "location",
                        "updated_at",
                    ]
                )

            event_type = "OFFLINE_MEETING_CREATED"

        else:
            event_type = "MEETING_CREATED"

        context = {
            "manager_name": (manager.get_full_name() or manager.username),
            "employee_name": (
                meeting.created_by.get_full_name() or meeting.created_by.username
            ),
            "meeting_title": meeting.meeting_title,
            "meeting_date": str(meeting.meeting_date),
            "start_time": str(meeting.start_time),
            "end_time": str(meeting.end_time),
            "meeting_link": (meeting.meeting_link or "Will be shared after approval"),
            "location": (meeting.location or OFFICE_LOCATION),
        }

        # ==================================================
        # TEMPLATE BASED NOTIFICATION
        # ==================================================

        trigger_notification_event(
            event_type=event_type,
            recipient=manager,
            context=context,
            template_id=template_id,
        )

        # ==================================================
        # DIRECT EMAIL TO MANAGER
        # ==================================================

        if manager.email:

            send_mail(
                subject=(f"Meeting Approval Required: " f"{meeting.meeting_title}"),
                message=(
                    f"Hello {manager.username},\n\n"
                    f"{meeting.created_by.get_full_name() or meeting.created_by.username} "
                    f"has requested a meeting.\n\n"
                    f"Meeting: "
                    f"{meeting.meeting_title}\n"
                    f"Date: "
                    f"{meeting.meeting_date}\n"
                    f"Time: "
                    f"{meeting.start_time} - "
                    f"{meeting.end_time}\n"
                    f"Link: "
                    f"{meeting.meeting_link or 'Will be shared after approval'}\n"
                    f"Location: "
                    f"{meeting.location or OFFICE_LOCATION}\n\n"
                    "Please approve or reject "
                    "this meeting.\n\n"
                    "Regards,\n"
                    "CRM Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[manager.email.strip()],
                fail_silently=False,
            )

        logger.info(
            "Manager notified: meeting_id=%s " "event=%s template_id=%s",
            meeting_id,
            event_type,
            template_id,
        )

        return True

    except Exception:

        logger.exception(
            "Manager notification failed: " "meeting_id=%s",
            meeting_id,
        )

        return False


# ======================================================
# APPROVED MEETING
#
# SEND EMAIL + NOTIFICATION TO:
# EMPLOYEE + MANAGER + CUSTOMER
# ======================================================


@shared_task
def send_approved_meeting(meeting_id):

    try:

        meeting = Meeting.objects.select_related(
            "created_by",
            "manager",
            "lead",
            "meeting_type_id",
        ).get(meeting_id=meeting_id)

        # Safety
        if meeting.approval_status != Meeting.ApprovalStatus.APPROVED:
            logger.warning(
                "Meeting not approved: meeting_id=%s",
                meeting_id,
            )
            return False

        # Type check
        m_type_id = None
        m_type_name = ""
        if meeting.meeting_type_id:
            m_type_id = getattr(meeting.meeting_type_id, "meeting_type_id", None)
            m_type_name = (
                getattr(meeting.meeting_type_id, "type_name", "") or ""
            ).lower()

        is_online = (m_type_id == ONLINE_MEETING_TYPE_ID) or ("online" in m_type_name)

        # Online meeting ke liye link auto generate agar na ho
        if not meeting.meeting_link and is_online:
            meet_link = generate_google_meet_link(meeting)
            if meet_link:
                meeting.meeting_link = meet_link
                meeting.save(
                    update_fields=[
                        "meeting_link",
                        "updated_at",
                    ]
                )

        # ==================================================
        # SEND EMAILS (Employee + Manager + Client)
        # ==================================================

        send_meeting_scheduled_emails(meeting)

        # ==================================================
        # IN-APP + TEMPLATE NOTIFICATION
        # ==================================================

        context = {
            "meeting_title": meeting.meeting_title,
            "meeting_date": str(meeting.meeting_date),
            "start_time": str(meeting.start_time),
            "end_time": str(meeting.end_time),
            "meeting_link": (meeting.meeting_link or "N/A"),
            "location": (meeting.location or OFFICE_LOCATION),
        }

        recipients = []

        if meeting.created_by:
            recipients.append(meeting.created_by)

        if meeting.manager:
            recipients.append(meeting.manager)

        if recipients:
            trigger_notification_event(
                event_type="MEETING_APPROVED",
                recipient=recipients,
                context=context,
            )

        logger.info(
            "Approved meeting workflow done: " "meeting_id=%s",
            meeting_id,
        )

        return True

    except Exception:

        logger.exception(
            "Approved meeting task failed: " "meeting_id=%s",
            meeting_id,
        )

        return False


# ======================================================
# REJECTED MEETING
# ======================================================


@shared_task
def notify_employee_meeting_rejected(meeting_id):

    try:

        meeting = Meeting.objects.select_related(
            "created_by",
            "manager",
        ).get(meeting_id=meeting_id)

        employee = meeting.created_by

        if not employee:
            return False

        # ==================================================
        # TEMPLATE BASED NOTIFICATION
        # ==================================================

        context = {
            "employee_name": (employee.get_full_name() or employee.username),
            "meeting_title": meeting.meeting_title,
            "rejection_reason": (meeting.rejection_reason or "No reason provided"),
            "manager_name": (
                meeting.manager.get_full_name() or meeting.manager.username
                if meeting.manager
                else "Manager"
            ),
        }

        trigger_notification_event(
            event_type="MEETING_REJECTED",
            recipient=employee,
            context=context,
        )

        # ==================================================
        # EMAIL
        # ==================================================

        if employee.email:

            send_mail(
                subject=(f"Meeting Cancelled: " f"{meeting.meeting_title}"),
                message=(
                    f"Hello {employee.username},\n\n"
                    f"Your meeting "
                    f"'{meeting.meeting_title}' "
                    f"has been cancelled/rejected "
                    f"by manager.\n\n"
                    f"Reason:\n"
                    f"{meeting.rejection_reason}\n\n"
                    "Please reschedule the meeting "
                    "and submit again.\n\n"
                    "Regards,\n"
                    "CRM Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[employee.email.strip()],
                fail_silently=False,
            )

        return True

    except Exception:

        logger.exception(
            "Rejected meeting notification failed: " "meeting_id=%s",
            meeting_id,
        )

        return False


# ======================================================
# RESCHEDULED MEETING
#
# SEND AGAIN TO MANAGER
# ======================================================


@shared_task
def notify_manager_about_reschedule(meeting_id):

    try:

        meeting = Meeting.objects.select_related(
            "manager",
            "created_by",
        ).get(meeting_id=meeting_id)

        manager = meeting.manager

        if not manager:
            return False

        create_notification(
            user=manager,
            title="Meeting Rescheduled - Approval Required",
            message=(
                f"{meeting.created_by.username} "
                f"rescheduled "
                f"'{meeting.meeting_title}'. "
                f"New date: {meeting.meeting_date}, "
                f"new time: {meeting.start_time}. "
                f"Please approve again."
            ),
            type_name="Meeting Rescheduled",
        )

        if manager.email:

            send_mail(
                subject=(
                    f"Meeting Rescheduled - "
                    f"Approval Required: "
                    f"{meeting.meeting_title}"
                ),
                message=(
                    f"Hello {manager.username},\n\n"
                    f"The employee has rescheduled "
                    f"the meeting.\n\n"
                    f"Meeting: "
                    f"{meeting.meeting_title}\n"
                    f"New Date: "
                    f"{meeting.meeting_date}\n"
                    f"New Time: "
                    f"{meeting.start_time} - "
                    f"{meeting.end_time}\n\n"
                    "Please approve or reject "
                    "the meeting again.\n\n"
                    "Regards,\n"
                    "CRM Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[manager.email.strip()],
                fail_silently=False,
            )

        return True

    except Exception:

        logger.exception(
            "Rescheduled meeting notification failed: " "meeting_id=%s",
            meeting_id,
        )

        return False
