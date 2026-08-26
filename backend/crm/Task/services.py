# ======================================================
# TASK / MEETING SERVICES
# ======================================================

import logging

from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import (
    Reminder,
    ReminderStatus,
    ReminderType,
    Task,
)
from Notification.notification_utils import create_notification
import uuid
import os

try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account

    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False

logger = logging.getLogger(__name__)


# ======================================================
# MEETING TYPE CONSTANTS
# ======================================================

ONLINE_MEETING_TYPE_ID = 1  # MeetingType id=1 = Online
OFFLINE_MEETING_TYPE_ID = 2  # MeetingType id=2 = Offline


OFFICE_LOCATION = "123, Business Park, Ahmedabad, Gujarat - 380015"


# ======================================================
# GOOGLE MEET LINK GENERATOR
# ======================================================


def generate_google_meet_link(meeting):
    try:
        service_account_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")

        if (
            HAS_GOOGLE_API
            and service_account_file
            and os.path.exists(service_account_file)
        ):
            calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
            SCOPES = ["https://www.googleapis.com/auth/calendar"]

            credentials = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=SCOPES,
            )

            service = build("calendar", "v3", credentials=credentials)

            meeting_date = str(meeting.meeting_date)
            start_dt = f"{meeting_date}T{meeting.start_time}+05:30"
            end_dt = f"{meeting_date}T{meeting.end_time}+05:30"

            event = {
                "summary": meeting.meeting_title,
                "description": meeting.description or "",
                "start": {
                    "dateTime": start_dt,
                    "timeZone": "Asia/Kolkata",
                },
                "end": {
                    "dateTime": end_dt,
                    "timeZone": "Asia/Kolkata",
                },
                "conferenceData": {
                    "createRequest": {
                        "requestId": str(uuid.uuid4()),
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
            }

            created_event = (
                service.events()
                .insert(
                    calendarId=calendar_id,
                    body=event,
                    conferenceDataVersion=1,
                )
                .execute()
            )

            meet_link = created_event.get("hangoutLink")
            if meet_link:
                logger.info(
                    "Google Meet link generated via Google Calendar API: meeting_id=%s link=%s",
                    getattr(meeting, "meeting_id", None),
                    meet_link,
                )
                return meet_link

    except Exception:
        logger.warning(
            "Google Calendar API unavailable for meeting_id=%s, using fallback link generator",
            getattr(meeting, "meeting_id", None),
        )

    # Fallback standard Google Meet link
    random_code = (
        f"{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:3]}"
    )
    meet_link = f"https://meet.google.com/{random_code}"
    logger.info(
        "Generated fallback Google Meet link: meeting_id=%s link=%s",
        getattr(meeting, "meeting_id", None),
        meet_link,
    )
    return meet_link


# ======================================================
# MEETING EMAIL HELPERS
# ======================================================


def _get_meeting_lead_name(meeting):
    """
    Get customer / lead name safely.
    """

    lead = getattr(meeting, "lead", None)

    if not lead:
        return "Customer"

    return getattr(lead, "name", None) or "Customer"


def _get_customer_email(meeting):
    """
    Get customer email safely from Lead.
    """

    lead = getattr(meeting, "lead", None)

    if not lead:
        return None

    email = getattr(
        lead,
        "email",
        None,
    )

    if not email:
        return None

    email = email.strip()

    return email or None


def _get_meeting_details(meeting):
    """
    Return common meeting information.
    """

    return {
        "title": getattr(
            meeting,
            "meeting_title",
            "Meeting",
        ),
        "date": getattr(
            meeting,
            "meeting_date",
            "",
        ),
        "start_time": getattr(
            meeting,
            "start_time",
            "",
        ),
        "end_time": getattr(
            meeting,
            "end_time",
            "",
        ),
        "location": (
            getattr(
                meeting,
                "location",
                None,
            )
            or "Online / Office"
        ),
        "description": (
            getattr(
                meeting,
                "description",
                None,
            )
            or "N/A"
        ),
        "meeting_link": (
            getattr(
                meeting,
                "meeting_link",
                None,
            )
            or "Not available"
        ),
        "lead_name": _get_meeting_lead_name(meeting),
        "customer_email": _get_customer_email(meeting),
    }


def _get_meeting_type_info(meeting):
    """
    DRY: Detect meeting type (online/offline/custom).
    Returns (is_online, is_offline).
    """
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
    return is_online, is_offline


def _get_unique_emails(emails):
    """
    Remove empty and duplicate emails.
    """

    cleaned = []

    for email in emails:

        if not email:
            continue

        email = email.strip()

        if not email:
            continue

        if email not in cleaned:
            cleaned.append(email)

    return cleaned


def _send_email_to_each_recipient(*, subject, message, recipients):
    """Send independently so one bad address cannot block other recipients."""
    sent_recipients = []

    for recipient in _get_unique_emails(recipients):
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            sent_recipients.append(recipient)
        except Exception:
            logger.exception(
                "Email delivery failed for recipient=%s",
                recipient,
            )

    return sent_recipients


# ======================================================
# ======================================================
# MANAGER APPROVAL EMAIL
# ======================================================
# ======================================================


def send_manager_meeting_approval_email(meeting):
    """
    Send meeting approval request to manager.

    This is called when employee creates a meeting.

    IMPORTANT:
    Customer does NOT receive any email here.
    """

    try:

        manager = getattr(
            meeting,
            "manager",
            None,
        )

        if not manager:

            logger.warning(
                "Manager missing for meeting approval: " "meeting_id=%s",
                getattr(
                    meeting,
                    "meeting_id",
                    None,
                ),
            )

            return False

        manager_email = getattr(
            manager,
            "email",
            None,
        )

        if not manager_email:

            logger.warning(
                "Manager email missing: " "meeting_id=%s manager_id=%s",
                getattr(
                    meeting,
                    "meeting_id",
                    None,
                ),
                getattr(
                    manager,
                    "pk",
                    None,
                ),
            )

            return False

        details = _get_meeting_details(meeting)

        employee = getattr(
            meeting,
            "created_by",
            None,
        )

        employee_name = (
            getattr(
                employee,
                "username",
                None,
            )
            or "Employee"
        )

        subject = f"Meeting Approval Required: " f"{details['title']}"

        message = (
            f"Hello {getattr(manager, 'username', 'Manager')},\n\n"
            f"{employee_name} has requested a meeting "
            f"that requires your approval.\n\n"
            f"Meeting Title: "
            f"{details['title']}\n"
            f"Customer: "
            f"{details['lead_name']}\n"
            f"Date: "
            f"{details['date']}\n"
            f"Time: "
            f"{details['start_time']} - "
            f"{details['end_time']}\n"
            f"Location: "
            f"{details['location']}\n"
            f"Description: "
            f"{details['description']}\n\n"
            f"Please open the CRM and "
            f"approve or reject this meeting.\n\n"
            f"Regards,\n"
            f"CRM System"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[manager_email.strip()],
            fail_silently=False,
        )

        logger.info(
            "Manager approval email sent: " "meeting_id=%s manager=%s",
            meeting.meeting_id,
            manager_email,
        )

        return True

    except Exception:

        logger.exception(
            "Error sending manager approval email: " "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return False


# ======================================================
# MANAGER APPROVAL NOTIFICATION
# ======================================================


def create_manager_meeting_approval_notification(
    meeting,
):
    """
    Create in-app notification for manager.
    """

    try:

        manager = getattr(
            meeting,
            "manager",
            None,
        )

        if not manager:
            return False

        employee = getattr(
            meeting,
            "created_by",
            None,
        )

        employee_name = (
            getattr(
                employee,
                "username",
                None,
            )
            or "Employee"
        )

        create_notification(
            user=manager,
            title="Meeting Approval Required",
            message=(
                f"{employee_name} requested meeting "
                f"'{meeting.meeting_title}' "
                f"on {meeting.meeting_date} "
                f"at {meeting.start_time}. "
                f"Please approve or reject it."
            ),
            type_name="Meeting Approval",
        )

        logger.info(
            "Manager meeting approval notification created: "
            "meeting_id=%s manager_id=%s",
            meeting.meeting_id,
            getattr(
                manager,
                "pk",
                None,
            ),
        )

        return True

    except Exception:

        logger.exception(
            "Error creating manager approval notification: " "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return False


# ======================================================
# EMPLOYEE MEETING REJECTED EMAIL
# ======================================================


def send_meeting_rejected_email(meeting):
    """
    Notify employee that manager rejected the meeting.
    """

    try:

        employee = getattr(
            meeting,
            "created_by",
            None,
        )

        if not employee:
            return False

        employee_email = getattr(
            employee,
            "email",
            None,
        )

        if not employee_email:
            return False

        manager = getattr(
            meeting,
            "manager",
            None,
        )

        manager_name = (
            getattr(
                manager,
                "username",
                None,
            )
            or "Manager"
        )

        reason = (
            getattr(
                meeting,
                "rejection_reason",
                None,
            )
            or "No reason provided."
        )

        subject = f"Meeting Rejected: " f"{meeting.meeting_title}"

        message = (
            f"Hello {employee.username},\n\n"
            f"Your meeting "
            f"'{meeting.meeting_title}' "
            f"has been rejected by "
            f"{manager_name}.\n\n"
            f"Reason:\n"
            f"{reason}\n\n"
            f"Please reschedule the meeting "
            f"and submit it for manager approval again.\n\n"
            f"Regards,\n"
            f"CRM System"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[employee_email.strip()],
            fail_silently=False,
        )

        logger.info(
            "Meeting rejection email sent: " "meeting_id=%s employee=%s",
            meeting.meeting_id,
            employee_email,
        )

        return True

    except Exception:

        logger.exception(
            "Error sending meeting rejection email: " "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return False


# ======================================================
# EMPLOYEE REJECTION NOTIFICATION
# ======================================================


def create_meeting_rejected_notification(
    meeting,
):
    """
    Create in-app rejection notification for employee.
    """

    try:

        employee = getattr(
            meeting,
            "created_by",
            None,
        )

        if not employee:
            return False

        manager = getattr(
            meeting,
            "manager",
            None,
        )

        manager_name = (
            getattr(
                manager,
                "username",
                None,
            )
            or "Manager"
        )

        reason = (
            getattr(
                meeting,
                "rejection_reason",
                None,
            )
            or "No reason provided."
        )

        create_notification(
            user=employee,
            title="Meeting Rejected",
            message=(
                f"Meeting '{meeting.meeting_title}' "
                f"was rejected by {manager_name}. "
                f"Reason: {reason}. "
                f"Please reschedule the meeting."
            ),
            type_name="Meeting Rejected",
        )

        return True

    except Exception:

        logger.exception(
            "Error creating meeting rejection notification: " "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return False


# ======================================================
# RESCHEDULED MEETING
# SEND APPROVAL REQUEST AGAIN
# ======================================================


def send_rescheduled_meeting_approval_email(
    meeting,
):
    """
    After employee reschedules a rejected meeting,
    send approval request to manager again.
    """

    try:

        manager = getattr(
            meeting,
            "manager",
            None,
        )

        if not manager:
            return False

        manager_email = getattr(
            manager,
            "email",
            None,
        )

        if not manager_email:
            return False

        employee = getattr(
            meeting,
            "created_by",
            None,
        )

        employee_name = (
            getattr(
                employee,
                "username",
                None,
            )
            or "Employee"
        )

        details = _get_meeting_details(meeting)

        subject = f"Meeting Rescheduled - Approval Required: " f"{details['title']}"

        message = (
            f"Hello {manager.username},\n\n"
            f"{employee_name} has rescheduled "
            f"the previously rejected meeting.\n\n"
            f"Meeting Title: "
            f"{details['title']}\n"
            f"Customer: "
            f"{details['lead_name']}\n"
            f"New Date: "
            f"{details['date']}\n"
            f"New Time: "
            f"{details['start_time']} - "
            f"{details['end_time']}\n"
            f"Location: "
            f"{details['location']}\n"
            f"Description: "
            f"{details['description']}\n\n"
            f"Please approve or reject "
            f"the meeting again.\n\n"
            f"Regards,\n"
            f"CRM System"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[manager_email.strip()],
            fail_silently=False,
        )

        logger.info(
            "Rescheduled meeting approval email sent: " "meeting_id=%s manager=%s",
            meeting.meeting_id,
            manager_email,
        )

        return True

    except Exception:

        logger.exception(
            "Error sending rescheduled meeting approval email: " "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return False


# ======================================================
# APPROVED MEETING
# SEND EMAIL TO:
#
# 1. EMPLOYEE
# 2. MANAGER
# 3. CUSTOMER
# ======================================================


def send_meeting_scheduled_emails(meeting):
    """
    Called ONLY after manager approves meeting.

    Type 1 (Online)  → Google Meet link bhejo
    Type 2 (Offline) → Static office location bhejo

    Recipients: Employee + Manager + Client (Lead)
    """

    try:

        details = _get_meeting_details(meeting)

        employee = getattr(meeting, "created_by", None)
        manager = getattr(meeting, "manager", None)
        customer_email = details["customer_email"]

        # Type check
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

        if is_online:
            join_line = (
                f"Google Meet Link: {details['meeting_link']}\n"
                f"Click the link above to join the meeting."
            )
        elif is_offline:
            loc = (
                details["location"]
                if details["location"] and details["location"] != "Online / Office"
                else OFFICE_LOCATION
            )
            join_line = f"Meeting Location: {loc}"
        else:
            loc = (
                details["location"]
                if details["location"] and details["location"] != "Online / Office"
                else "To be coordinated"
            )
            join_line = f"Meeting Mode / Location: {loc}"

        # Extra fields (Template 3 custom fields)
        extra_fields = getattr(meeting, "extra_fields", {}) or {}
        custom_block = ""
        if isinstance(extra_fields, dict) and extra_fields:
            extras_str = "\n".join(
                f"• {k.replace('_', ' ').title()}: {v}" for k, v in extra_fields.items()
            )
            custom_block = f"\nCustom Meeting Details:\n{extras_str}\n"

        recipients = []

        if employee:
            emp_email = getattr(employee, "email", None)
            if emp_email:
                recipients.append(emp_email)

        if manager:
            mgr_email = getattr(manager, "email", None)
            if mgr_email:
                recipients.append(mgr_email)

        if customer_email:
            recipients.append(customer_email)

        recipients = _get_unique_emails(recipients)

        if not recipients:
            logger.warning(
                "No recipients for approved meeting: " "meeting_id=%s",
                meeting.meeting_id,
            )
            return False

        subject = f"Meeting Scheduled: {details['title']}"

        message = (
            f"Hello,\n\n"
            f"The meeting has been approved "
            f"and scheduled successfully.\n\n"
            f"Meeting Title: {details['title']}\n"
            f"Customer: {details['lead_name']}\n"
            f"Date: {details['date']}\n"
            f"Time: {details['start_time']} - {details['end_time']}\n"
            f"{join_line}\n"
            f"{custom_block}"
            f"Description: {details['description']}\n\n"
            f"Please be ready at the scheduled time.\n\n"
            f"Regards,\nCRM System"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )

        logger.info(
            "Approved meeting emails sent: " "meeting_id=%s recipients=%s",
            meeting.meeting_id,
            recipients,
        )

        return True

    except Exception:

        logger.exception(
            "Error sending approved meeting emails: " "meeting_id=%s",
            getattr(meeting, "meeting_id", None),
        )

        return False


# ======================================================
# 5-MINUTE MEETING REMINDER
#
# EMPLOYEE + MANAGER + CUSTOMER
# ======================================================


def send_meeting_5_minute_reminder(
    meeting,
):
    """
    5 min pehle reminder bhejo:
    Employee + Manager + Client (Lead) teeno ko.

    Online  → Meet link include
    Offline → Office location include
    Custom  → Custom details include
    """

    try:

        details = _get_meeting_details(meeting)

        employee = getattr(meeting, "created_by", None)
        manager = getattr(meeting, "manager", None)

        # Type check
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

        if is_online:
            join_line = (
                f"Google Meet Link: {details['meeting_link']}\n"
                f"Click the link to join."
            )
        elif is_offline:
            loc = (
                details["location"]
                if details["location"] and details["location"] != "Online / Office"
                else OFFICE_LOCATION
            )
            join_line = f"Meeting Location: {loc}"
        else:
            loc = (
                details["location"]
                if details["location"] and details["location"] != "Online / Office"
                else "To be coordinated"
            )
            join_line = f"Meeting Mode / Location: {loc}"

        extra_fields = getattr(meeting, "extra_fields", {}) or {}
        custom_block = ""
        if isinstance(extra_fields, dict) and extra_fields:
            extras_str = "\n".join(
                f"• {k.replace('_', ' ').title()}: {v}" for k, v in extra_fields.items()
            )
            custom_block = f"\nCustom Meeting Details:\n{extras_str}\n"

        recipients = []

        if employee:
            emp_email = getattr(employee, "email", None)
            if emp_email:
                recipients.append(emp_email)

        if manager:
            mgr_email = getattr(manager, "email", None)
            if mgr_email:
                recipients.append(mgr_email)

        if details["customer_email"]:
            recipients.append(details["customer_email"])

        recipients = _get_unique_emails(recipients)

        if not recipients:
            logger.warning(
                "No recipients for 5-minute reminder: " "meeting_id=%s",
                meeting.meeting_id,
            )
            return False

        subject = f"Meeting Reminder - " f"Starts in 5 Minutes: " f"{details['title']}"

        message = (
            f"Hello,\n\n"
            f"Your meeting starts in 5 minutes!\n\n"
            f"Meeting Title: {details['title']}\n"
            f"Customer: {details['lead_name']}\n"
            f"Date: {details['date']}\n"
            f"Time: {details['start_time']} - {details['end_time']}\n"
            f"{join_line}\n"
            f"{custom_block}"
            f"Please be ready.\n\n"
            f"Regards,\nCRM System"
        )

        sent_recipients = _send_email_to_each_recipient(
            subject=subject,
            message=message,
            recipients=recipients,
        )

        logger.info(
            "5-minute reminder sent: " "meeting_id=%s recipients=%s",
            meeting.meeting_id,
            sent_recipients,
        )

        return bool(sent_recipients)

    except Exception:

        logger.exception(
            "Error sending 5-minute reminder: " "meeting_id=%s",
            getattr(meeting, "meeting_id", None),
        )

        return False


# ======================================================
# 5-MINUTE MEETING REMINDER
# IN-APP NOTIFICATIONS
# ======================================================


# ======================================================
# ======================================================
# OLD REMINDER DATABASE FUNCTION
# ======================================================
# ======================================================


def create_meeting_reminder(
    meeting,
    reminder_for,
    minutes_before=5,
):
    """
    Create database Reminder record.

    IMPORTANT:
    Default is now 5 minutes, not 15.
    """

    try:

        if not meeting:

            logger.warning("Meeting reminder not created: " "meeting missing.")

            return None

        if not reminder_for:

            logger.warning("Meeting reminder not created: " "reminder_for missing.")

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
                "Meeting reminder not created: " "date/time missing meeting_id=%s",
                getattr(
                    meeting,
                    "meeting_id",
                    None,
                ),
            )

            return None

        combined_datetime = datetime.combine(
            meeting_date,
            start_time,
        )

        if timezone.is_naive(combined_datetime):

            meeting_datetime = timezone.make_aware(combined_datetime)

        else:

            meeting_datetime = combined_datetime

        reminder_datetime = meeting_datetime - timedelta(minutes=minutes_before)

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
                f"Reminder: "
                f"{meeting.meeting_title} "
                f"is scheduled at "
                f"{start_time}."
            ),
            created_by=meeting.created_by,
            is_sent=False,
        )

        logger.info(
            "Meeting reminder created: "
            "reminder_id=%s meeting_id=%s "
            "reminder_for=%s reminder_datetime=%s",
            reminder.reminder_id,
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
            getattr(
                reminder_for,
                "pk",
                None,
            ),
            reminder.reminder_datetime,
        )

        return reminder

    except Exception:

        logger.exception(
            "Error creating meeting reminder: " "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return None


# ======================================================
# CREATE MEETING DATABASE RECORDS
#
# IMPORTANT:
# DO NOT CREATE REMINDER BEFORE APPROVAL
# ======================================================


def create_meeting_database_records(
    meeting,
):
    """
    Create database notifications related to meeting.

    IMPORTANT:
    This function DOES NOT create a meeting reminder
    before manager approval.

    Manager approval notification is handled separately.
    """

    try:

        with transaction.atomic():

            # ==============================================
            # MANAGER APPROVAL NOTIFICATION
            # ==============================================

            create_manager_meeting_approval_notification(meeting)

        logger.info(
            "Meeting approval database workflow completed: " "meeting_id=%s",
            meeting.meeting_id,
        )

        return True

    except Exception:

        logger.exception(
            "Meeting database workflow failed: " "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return False


# ======================================================
# MEETING CREATION WORKFLOW
#
# IMPORTANT:
# DO NOT SEND CUSTOMER EMAIL HERE
# ======================================================


def send_meeting_creation_emails(
    meeting,
):
    """
    Called when employee creates a meeting.

    NEW WORKFLOW:

        Employee
            ↓
        Meeting created
            ↓
        Manager approval request

    NO customer email is sent here.

    NO meeting reminder is created here.

    Customer receives meeting email ONLY after
    manager approves.
    """

    try:

        # ==============================================
        # MANAGER EMAIL
        # ==============================================

        send_manager_meeting_approval_email(meeting)

        # ==============================================
        # MANAGER IN-APP NOTIFICATION
        # ==============================================

        create_manager_meeting_approval_notification(meeting)

        logger.info(
            "Meeting creation approval workflow completed: " "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return True

    except Exception:

        logger.exception(
            "Unexpected error in meeting creation workflow: " "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return False


# ======================================================
# APPROVED MEETING WORKFLOW
# ======================================================


def process_approved_meeting(
    meeting,
):
    """
    Called AFTER manager approves meeting.

    Does:

        1. Employee scheduled email
        2. Manager scheduled email
        3. Customer scheduled email
        4. Creates 5-minute reminder records if needed
    """

    try:

        # ==============================================
        # SAFETY CHECK
        # ==============================================

        approval_status = getattr(
            meeting,
            "approval_status",
            None,
        )

        if approval_status != "APPROVED":

            logger.warning(
                "Meeting is not approved: " "meeting_id=%s status=%s",
                getattr(
                    meeting,
                    "meeting_id",
                    None,
                ),
                approval_status,
            )

            return False

        # ==============================================
        # MEETING LINK (online only)
        # ==============================================

        is_online, is_offline = _get_meeting_type_info(meeting)

        if is_online and not getattr(meeting, "meeting_link", None):

            logger.warning(
                "Approved online meeting has no meeting link: meeting_id=%s",
                meeting.meeting_id,
            )

            return False

        # ==============================================
        # SEND EMAIL TO ALL 3
        # ==============================================

        email_success = send_meeting_scheduled_emails(meeting)

        if not email_success:

            logger.warning(
                "Scheduled meeting email failed: " "meeting_id=%s",
                meeting.meeting_id,
            )

        # ==============================================
        # CREATE EMPLOYEE NOTIFICATION
        # ==============================================

        employee = getattr(
            meeting,
            "created_by",
            None,
        )

        if employee:

            create_notification(
                user=employee,
                title=(f"Meeting Scheduled: " f"{meeting.meeting_title}"),
                message=(
                    f"Your meeting has been approved "
                    f"and scheduled for "
                    f"{meeting.meeting_date} "
                    f"at {meeting.start_time}."
                ),
                type_name="Meeting Scheduled",
            )

        # ==============================================
        # CREATE MANAGER NOTIFICATION
        # ==============================================

        manager = getattr(
            meeting,
            "manager",
            None,
        )

        if manager:

            create_notification(
                user=manager,
                title=(f"Meeting Scheduled: " f"{meeting.meeting_title}"),
                message=(
                    f"Meeting is scheduled for "
                    f"{meeting.meeting_date} "
                    f"at {meeting.start_time}."
                ),
                type_name="Meeting Scheduled",
            )

        logger.info(
            "Approved meeting workflow completed: " "meeting_id=%s",
            meeting.meeting_id,
        )

        return True

    except Exception:

        logger.exception(
            "Approved meeting processing failed: " "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return False


# ======================================================
# REJECTED MEETING WORKFLOW
# ======================================================


def process_rejected_meeting(
    meeting,
):
    """
    Called after manager rejects meeting.

    Employee receives:
        - Email
        - In-app notification

    Customer receives nothing.
    """

    try:

        email_success = send_meeting_rejected_email(meeting)

        notification_success = create_meeting_rejected_notification(meeting)

        logger.info(
            "Rejected meeting workflow completed: "
            "meeting_id=%s email=%s notification=%s",
            meeting.meeting_id,
            email_success,
            notification_success,
        )

        return email_success or notification_success

    except Exception:

        logger.exception(
            "Rejected meeting processing failed: " "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return False


# ======================================================
# RESCHEDULED MEETING WORKFLOW
# ======================================================


def process_rescheduled_meeting(
    meeting,
):
    """
    Called after employee reschedules rejected meeting.

    Meeting status should already be reset to:

        PENDING

    Manager receives approval request again.

    Customer receives nothing.
    """

    try:

        approval_status = getattr(
            meeting,
            "approval_status",
            None,
        )

        if approval_status != "PENDING":

            logger.warning(
                "Rescheduled meeting is not pending: " "meeting_id=%s status=%s",
                meeting.meeting_id,
                approval_status,
            )

            return False

        email_success = send_rescheduled_meeting_approval_email(meeting)

        notification_success = create_manager_meeting_approval_notification(meeting)

        logger.info(
            "Rescheduled meeting workflow completed: " "meeting_id=%s",
            meeting.meeting_id,
        )

        return email_success or notification_success

    except Exception:

        logger.exception(
            "Rescheduled meeting processing failed: " "meeting_id=%s",
            getattr(
                meeting,
                "meeting_id",
                None,
            ),
        )

        return False


# ======================================================
# PROCESS DUE MEETING REMINDERS
#
# OLD REMINDER TABLE SYSTEM
#
# This remains for your existing Reminder APIs.
# ======================================================


def send_due_reminder_notification(
    reminder,
):
    """
    Send due reminder email + notification.

    For meeting reminders, only APPROVED meetings
    are allowed.
    """

    try:

        meeting = getattr(
            reminder,
            "meeting_id",
            None,
        )

        # ==================================================
        # MEETING REMINDER
        # ==================================================

        if meeting:

            approval_status = getattr(
                meeting,
                "approval_status",
                None,
            )

            # ----------------------------------------------
            # NEVER SEND REMINDER FOR:
            #
            # PENDING
            # REJECTED
            # ----------------------------------------------

            if approval_status != "APPROVED":

                logger.info(
                    "Skipping reminder because meeting "
                    "is not approved: meeting_id=%s "
                    "status=%s",
                    getattr(
                        meeting,
                        "meeting_id",
                        None,
                    ),
                    approval_status,
                )

                return False

            # ----------------------------------------------
            # 5 MINUTE REMINDER
            # ----------------------------------------------

            details = _get_meeting_details(meeting)

            recipients = []

            # Employee
            if meeting.created_by and getattr(
                meeting.created_by,
                "email",
                None,
            ):

                recipients.append(meeting.created_by.email)

            # Manager
            if getattr(
                meeting,
                "manager",
                None,
            ) and getattr(
                meeting.manager,
                "email",
                None,
            ):

                recipients.append(meeting.manager.email)

            # Customer
            if details["customer_email"]:

                recipients.append(details["customer_email"])

            recipients = _get_unique_emails(recipients)

            # ----------------------------------------------
            # IN-APP EMPLOYEE + MANAGER
            # ----------------------------------------------

            create_meeting_5_minute_notifications(meeting)

            # ----------------------------------------------
            # EMAIL
            # ----------------------------------------------

            sent_recipients = []
            if recipients:
                subject = (
                    f"Meeting Reminder - "
                    f"Starts in 5 Minutes: "
                    f"{details['title']}"
                )
                message = (
                    f"Hello,\n\n"
                    f"Your meeting "
                    f"'{details['title']}' "
                    f"will start in 5 minutes.\n\n"
                    f"Date: {details['date']}\n"
                    f"Time: {details['start_time']}\n"
                    f"Meeting Link: "
                    f"{details['meeting_link']}\n\n"
                    f"Regards,\n"
                    f"CRM System"
                )
                sent_recipients = _send_email_to_each_recipient(
                    subject=subject,
                    message=message,
                    recipients=recipients,
                )

                if not sent_recipients:
                    return False

            logger.info(
                "Meeting reminder sent: " "meeting_id=%s recipients=%s",
                meeting.meeting_id,
                sent_recipients,
            )

            return True

        # ==================================================
        # NORMAL TASK REMINDER
        # ==================================================

        target_user = getattr(
            reminder,
            "reminder_for",
            None,
        ) or getattr(
            reminder,
            "created_by",
            None,
        )

        if target_user:

            if getattr(
                reminder,
                "task_id",
                None,
            ):

                title = f"Task Reminder: " f"{reminder.task_id.task_title}"

            else:

                title = "Reminder Notification"

            create_notification(
                user=target_user,
                title=title,
                message=(reminder.message),
                type_name="Reminder",
            )

            if getattr(
                target_user,
                "email",
                None,
            ):

                send_mail(
                    subject=title,
                    message=(f"Hello,\n\n" f"{reminder.message}"),
                    from_email=(settings.DEFAULT_FROM_EMAIL),
                    recipient_list=[target_user.email],
                    fail_silently=False,
                )

        return True

    except Exception:

        logger.exception(
            "Error sending due reminder: " "reminder_id=%s",
            getattr(
                reminder,
                "reminder_id",
                None,
            ),
        )

        return False


# ======================================================
# PROCESS DUE REMINDERS
# ======================================================


def process_due_meeting_reminders():
    """
    Finds pending Reminder records whose time has arrived.

    Only approved meeting reminders are processed.
    """

    try:

        now = timezone.now()

        due_reminders = Reminder.objects.filter(
            is_sent=False,
            reminder_datetime__lte=now,
        ).select_related(
            "meeting_id",
            "meeting_id__lead",
            "meeting_id__created_by",
            "meeting_id__manager",
            "task_id",
            "reminder_for",
            "created_by",
        )[:100]

        sent_count = 0

        for reminder in due_reminders:

            try:

                success = send_due_reminder_notification(reminder)

                if success:

                    reminder.is_sent = True

                    reminder.save(update_fields=["is_sent"])

                    sent_count += 1

                    logger.info(
                        "Due reminder processed: " "reminder_id=%s",
                        reminder.reminder_id,
                    )

                else:

                    logger.warning(
                        "Due reminder was not sent: " "reminder_id=%s",
                        reminder.reminder_id,
                    )

            except Exception:

                logger.exception(
                    "Error processing due reminder: " "reminder_id=%s",
                    reminder.reminder_id,
                )

        logger.info(
            "Due meeting reminders completed: " "sent_count=%s",
            sent_count,
        )

        return sent_count

    except Exception:

        logger.exception("Unexpected error while processing " "due meeting reminders.")

        return 0


# ======================================================
# ======================================================
# TASK DUE REMINDER
# ======================================================
# ======================================================


def process_due_task_reminders():
    """
    Finds active pending tasks where due_date <= today.

    Sends:
        - In-app notification
        - Email

    to assigned employee.
    """

    try:

        now = timezone.now()

        today_end = now.replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )

        pending_tasks = Task.objects.filter(
            is_active=True,
            status__status_name__iexact="Pending",
            due_date__isnull=False,
            due_date__lte=today_end,
        ).select_related(
            "assigned_to",
            "lead",
            "customer",
            "priority",
        )[:100]

        sent_count = 0

        for task in pending_tasks:

            employee = getattr(
                task,
                "assigned_to",
                None,
            )

            if not employee:
                continue

            # ==========================================
            # TARGET / CUSTOMER NAME
            # ==========================================

            if getattr(
                task,
                "lead",
                None,
            ):

                target_name = task.lead.name

            elif getattr(
                task,
                "customer",
                None,
            ):

                target_name = task.customer.name

            else:

                target_name = "General"

            # ==========================================
            # SUBJECT
            # ==========================================

            subject = f"Task Reminder: " f"'{task.task_title}' is due!"

            # ==========================================
            # MESSAGE
            # ==========================================

            message = (
                f"Hello {employee.username},\n\n"
                f"Reminder for your pending task:\n\n"
                f"Task: "
                f"{task.task_title}\n"
                f"Client: "
                f"{target_name}\n"
                f"Due Date: "
                f"{task.due_date.strftime('%d-%b-%Y')}\n"
                f"Description: "
                f"{task.description or 'No description'}\n\n"
                f"Best regards,\n"
                f"CRM System"
            )

            # ==========================================
            # IN-APP NOTIFICATION
            # ==========================================

            create_notification(
                user=employee,
                title=subject,
                message=(f"Task '{task.task_title}' " f"is due for {target_name}."),
                type_name="Task Reminder",
            )

            # ==========================================
            # EMAIL
            # ==========================================

            if getattr(
                employee,
                "email",
                None,
            ):

                try:

                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=(settings.DEFAULT_FROM_EMAIL),
                        recipient_list=[employee.email],
                        fail_silently=True,
                    )

                except Exception:

                    logger.exception(
                        "Task reminder email failed: " "task_id=%s",
                        getattr(
                            task,
                            "task_id",
                            None,
                        ),
                    )

            sent_count += 1

        logger.info(
            "Due task reminders processed: " "sent_count=%s",
            sent_count,
        )

        return sent_count

    except Exception:

        logger.exception("Error processing due task reminders.")

        return 0
