import logging

from celery import shared_task

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import Meeting

from .services import (
    process_due_task_reminders,
    send_meeting_scheduled_emails,
    send_meeting_5_minute_reminder,
)

from Notification.notification_utils import (
    create_notification,
)


logger = logging.getLogger(__name__)


# ======================================================
# EXISTING TASK REMINDER
# ======================================================

@shared_task
def task_due_reminder_job():

    logger.info(
        "Celery Job Started: Checking for due tasks..."
    )

    count = process_due_task_reminders()

    logger.info(
        "Celery Job Finished: Sent %s task reminders.",
        count,
    )

    return f"Processed {count} task reminders."


# ======================================================
# MEETING REMINDER JOB
#
# CELERY BEAT RUNS EVERY MINUTE
# ======================================================

@shared_task
def meeting_reminder_job():

    now = timezone.localtime()

    reminder_start = now + timezone.timedelta(
        minutes=4,
        seconds=30,
    )

    reminder_end = now + timezone.timedelta(
        minutes=5,
        seconds=30,
    )

    meetings = Meeting.objects.filter(
        approval_status=Meeting.ApprovalStatus.APPROVED,

        reminder_sent_at__isnull=True,

        meeting_date=reminder_start.date(),

        start_time__gte=reminder_start.time(),

        start_time__lte=reminder_end.time(),
    ).select_related(
        "created_by",
        "manager",
        "lead",
    )

    sent_count = 0

    for meeting in meetings:

        try:

            # Safety check
            if (
                meeting.approval_status
                != Meeting.ApprovalStatus.APPROVED
            ):
                continue

            success = (
                send_meeting_5_minute_reminder(
                    meeting
                )
            )

            if success:

                meeting.reminder_sent_at = (
                    timezone.now()
                )

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

                        title=(
                            f"Meeting Reminder: "
                            f"{meeting.meeting_title}"
                        ),

                        message=(
                            f"Meeting starts in 5 minutes "
                            f"at {meeting.start_time}."
                        ),

                        type_name="Meeting Reminder",
                    )

                # ==========================================
                # MANAGER IN-APP NOTIFICATION
                # ==========================================

                if meeting.manager:

                    create_notification(
                        user=meeting.manager,

                        title=(
                            f"Meeting Reminder: "
                            f"{meeting.meeting_title}"
                        ),

                        message=(
                            f"Meeting starts in 5 minutes "
                            f"at {meeting.start_time}."
                        ),

                        type_name="Meeting Reminder",
                    )

                sent_count += 1

                logger.info(
                    "5-minute reminder processed: "
                    "meeting_id=%s",
                    meeting.meeting_id,
                )

        except Exception:

            logger.exception(
                "Meeting reminder failed: meeting_id=%s",
                meeting.meeting_id,
            )

    return (
        f"Processed {sent_count} meeting reminders."
    )


# ======================================================
# MANAGER APPROVAL REQUEST
# ======================================================

@shared_task
def notify_manager_about_meeting(meeting_id):

    try:

        meeting = Meeting.objects.select_related(
            "manager",
            "created_by",
            "lead",
        ).get(
            meeting_id=meeting_id
        )

        # Safety
        if (
            meeting.approval_status
            != Meeting.ApprovalStatus.PENDING
        ):
            return False

        manager = meeting.manager

        if not manager:
            return False

        # ==============================================
        # IN-APP
        # ==============================================

        create_notification(
            user=manager,

            title="Meeting Approval Required",

            message=(
                f"{meeting.created_by.username} "
                f"requested meeting "
                f"'{meeting.meeting_title}' "
                f"on {meeting.meeting_date} "
                f"at {meeting.start_time}. "
                f"Please approve or reject it."
            ),

            type_name="Meeting Approval",
        )

        # ==============================================
        # EMAIL
        # ==============================================

        if manager.email:

            send_mail(
                subject=(
                    f"Meeting Approval Required: "
                    f"{meeting.meeting_title}"
                ),

                message=(
                    f"Hello {manager.username},\n\n"

                    f"Employee "
                    f"{meeting.created_by.username} "
                    f"has requested a meeting.\n\n"

                    f"Meeting: "
                    f"{meeting.meeting_title}\n"

                    f"Date: "
                    f"{meeting.meeting_date}\n"

                    f"Time: "
                    f"{meeting.start_time} - "
                    f"{meeting.end_time}\n\n"

                    "Please open the CRM and "
                    "approve or reject this meeting.\n\n"

                    "Regards,\n"
                    "CRM Team"
                ),

                from_email=settings.DEFAULT_FROM_EMAIL,

                recipient_list=[
                    manager.email.strip()
                ],

                fail_silently=False,
            )

        return True

    except Exception:

        logger.exception(
            "Manager approval notification failed: "
            "meeting_id=%s",
            meeting_id,
        )

        return False


# ======================================================
# APPROVED MEETING
#
# SEND EMAIL TO:
# EMPLOYEE + MANAGER + CUSTOMER
# ======================================================

@shared_task
def send_approved_meeting(meeting_id):

    try:

        meeting = Meeting.objects.select_related(
            "created_by",
            "manager",
            "lead",
        ).get(
            meeting_id=meeting_id
        )

        # ==============================================
        # SAFETY CHECK
        # ==============================================

        if (
            meeting.approval_status
            != Meeting.ApprovalStatus.APPROVED
        ):
            logger.warning(
                "Meeting is not approved: meeting_id=%s",
                meeting_id,
            )

            return False

        # ==============================================
        # MEETING LINK MUST EXIST
        # ==============================================

        if not meeting.meeting_link:

            logger.warning(
                "Approved meeting has no meeting link: "
                "meeting_id=%s",
                meeting_id,
            )

            return False

        # ==============================================
        # SEND ALL 3 EMAILS
        # ==============================================

        send_meeting_scheduled_emails(
            meeting
        )

        # ==============================================
        # EMPLOYEE NOTIFICATION
        # ==============================================

        if meeting.created_by:

            create_notification(
                user=meeting.created_by,

                title=(
                    f"Meeting Scheduled: "
                    f"{meeting.meeting_title}"
                ),

                message=(
                    f"Your meeting has been approved "
                    f"and scheduled for "
                    f"{meeting.meeting_date} "
                    f"at {meeting.start_time}."
                ),

                type_name="Meeting Scheduled",
            )

        # ==============================================
        # MANAGER NOTIFICATION
        # ==============================================

        if meeting.manager:

            create_notification(
                user=meeting.manager,

                title=(
                    f"Meeting Scheduled: "
                    f"{meeting.meeting_title}"
                ),

                message=(
                    f"Meeting is scheduled for "
                    f"{meeting.meeting_date} "
                    f"at {meeting.start_time}."
                ),

                type_name="Meeting Scheduled",
            )

        logger.info(
            "Approved meeting workflow completed: "
            "meeting_id=%s",
            meeting_id,
        )

        return True

    except Exception:

        logger.exception(
            "Approved meeting task failed: meeting_id=%s",
            meeting_id,
        )

        return False


# ======================================================
# REJECTED MEETING
#
# EMPLOYEE NOTIFICATION
# ======================================================

@shared_task
def notify_employee_meeting_rejected(
    meeting_id
):

    try:

        meeting = Meeting.objects.select_related(
            "created_by",
            "manager",
        ).get(
            meeting_id=meeting_id
        )

        employee = meeting.created_by

        if not employee:
            return False

        # ==============================================
        # IN-APP
        # ==============================================

        create_notification(
            user=employee,

            title="Meeting Rejected",

            message=(
                f"Your meeting "
                f"'{meeting.meeting_title}' "
                f"was rejected by "
                f"{meeting.manager.username}. "
                f"Reason: "
                f"{meeting.rejection_reason}"
            ),

            type_name="Meeting Rejected",
        )

        # ==============================================
        # EMAIL
        # ==============================================

        if employee.email:

            send_mail(
                subject=(
                    f"Meeting Rejected: "
                    f"{meeting.meeting_title}"
                ),

                message=(
                    f"Hello {employee.username},\n\n"

                    f"Your meeting "
                    f"'{meeting.meeting_title}' "
                    f"was rejected by manager.\n\n"

                    f"Reason:\n"
                    f"{meeting.rejection_reason}\n\n"

                    "Please reschedule the meeting "
                    "and submit it for approval again.\n\n"

                    "Regards,\n"
                    "CRM Team"
                ),

                from_email=settings.DEFAULT_FROM_EMAIL,

                recipient_list=[
                    employee.email.strip()
                ],

                fail_silently=False,
            )

        return True

    except Exception:

        logger.exception(
            "Rejected meeting notification failed: "
            "meeting_id=%s",
            meeting_id,
        )

        return False


# ======================================================
# RESCHEDULED MEETING
#
# SEND AGAIN TO MANAGER
# ======================================================

@shared_task
def notify_manager_about_reschedule(
    meeting_id
):

    try:

        meeting = Meeting.objects.select_related(
            "manager",
            "created_by",
        ).get(
            meeting_id=meeting_id
        )

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

                recipient_list=[
                    manager.email.strip()
                ],

                fail_silently=False,
            )

        return True

    except Exception:

        logger.exception(
            "Rescheduled meeting notification failed: "
            "meeting_id=%s",
            meeting_id,
        )

        return False