from django.db import models
from django.conf import settings


class NotificationEventType(models.TextChoices):
    # Task Events
    TASK_ASSIGNED = "TASK_ASSIGNED", "Task Assigned"
    TASK_COMPLETED = "TASK_COMPLETED", "Task Completed"
    TASK_UPDATED = "TASK_UPDATED", "Task Updated"
    TASK_REASSIGNED = "TASK_REASSIGNED", "Task Reassigned"
    TASK_DELETED = "TASK_DELETED", "Task Deleted"
    TASK_STATUS_CHANGED = "TASK_STATUS_CHANGED", "Task Status Changed"
    TASK_REMINDER = "TASK_REMINDER", "Task Reminder"

    # Meeting Events
    MEETING_CREATED = "MEETING_CREATED", "Meeting Created"
    MEETING_RESCHEDULED = "MEETING_RESCHEDULED", "Meeting Rescheduled"
    MEETING_STATUS_CHANGED = "MEETING_STATUS_CHANGED", "Meeting Status Changed"
    MEETING_PARTICIPANT_ADDED = "MEETING_PARTICIPANT_ADDED", "Meeting Participant Added"
    MEETING_PARTICIPANT_REMOVED = (
        "MEETING_PARTICIPANT_REMOVED",
        "Meeting Participant Removed",
    )

    # Online/Offline Meeting Template Events
    ONLINE_MEETING_CREATED = "ONLINE_MEETING_CREATED", "Online Meeting Created"
    OFFLINE_MEETING_CREATED = "OFFLINE_MEETING_CREATED", "Offline Meeting Created"
    MEETING_APPROVED = "MEETING_APPROVED", "Meeting Approved"
    MEETING_REJECTED = "MEETING_REJECTED", "Meeting Rejected"

    # Reminder Events
    REMINDER_CREATED = "REMINDER_CREATED", "Reminder Created"
    REMINDER_UPDATED = "REMINDER_UPDATED", "Reminder Updated"
    REMINDER_DELETED = "REMINDER_DELETED", "Reminder Deleted"
    REMINDER_STATUS_CHANGED = "REMINDER_STATUS_CHANGED", "Reminder Status Changed"

    # FollowUp Events
    FOLLOWUP_CREATED = "FOLLOWUP_CREATED", "Follow-up Created"
    FOLLOWUP_UPDATED = "FOLLOWUP_UPDATED", "Follow-up Updated"
    FOLLOWUP_DELETED = "FOLLOWUP_DELETED", "Follow-up Deleted"
    FOLLOWUP_NOTE_ADDED = "FOLLOWUP_NOTE_ADDED", "Follow-up Note Added"
    FOLLOWUP_COMPLETED = "FOLLOWUP_COMPLETED", "Follow-up Completed"
    FOLLOWUP_REMINDER = "FOLLOWUP_REMINDER", "Follow-up Reminder"

    # Quotation Events
    QUOTATION_CREATED = "QUOTATION_CREATED", "Quotation Created"
    QUOTATION_UPDATED = "QUOTATION_UPDATED", "Quotation Updated"
    QUOTATION_SENT = "QUOTATION_SENT", "Quotation Sent"
    QUOTATION_REVISION_CREATED = (
        "QUOTATION_REVISION_CREATED",
        "Quotation Revision Created",
    )
    QUOTATION_ACCEPTED = "QUOTATION_ACCEPTED", "Quotation Accepted"
    QUOTATION_CLIENT_REJECTED = (
        "QUOTATION_CLIENT_REJECTED",
        "Quotation Rejected by Client",
    )
    QUOTATION_EMAIL_SENT = "QUOTATION_EMAIL_SENT", "Quotation Email Sent"
    QUOTATION_SUBMITTED = "QUOTATION_SUBMITTED", "Quotation Submitted"
    QUOTATION_APPROVED = "QUOTATION_APPROVED", "Quotation Approved"
    QUOTATION_REJECTED = "QUOTATION_REJECTED", "Quotation Rejected"

    # Lead Events
    LEAD_CREATED = "LEAD_CREATED", "Lead Created"
    LEAD_ASSIGNED = "LEAD_ASSIGNED", "Lead Assigned"
    LEAD_STAGE_CHANGED = "LEAD_STAGE_CHANGED", "Lead Stage Changed"
    LEAD_MARKED_LOST = "LEAD_MARKED_LOST", "Lead Marked Lost"
    LEAD_REENGAGED = "LEAD_REENGAGED", "Lead Re-engaged"
    LEAD_CONVERTED = "LEAD_CONVERTED", "Lead Converted"

    # Activity & Call Events
    ACTIVITY_CREATED = "ACTIVITY_CREATED", "Activity Created"
    CALL_ATTEMPT_LOGGED = "CALL_ATTEMPT_LOGGED", "Call Attempt Logged"
    FORM_SUBMISSION_COMPLETED = "FORM_SUBMISSION_COMPLETED", "Form Submission Completed"

    # Accounts / User Events
    ROLE_CHANGED = "ROLE_CHANGED", "Role Changed"
    USER_ASSIGNED = "USER_ASSIGNED", "User Assigned"

    # Manual / Other Events
    MANUAL = "MANUAL", "Manual Notification"

    # CallForms Events
    ADHOC_FIELD_PROPOSED = "ADHOC_FIELD_PROPOSED", "Adhoc Field Proposed"
    CALL_ATTEMPT_LOGGED = "CALL_ATTEMPT_LOGGED", "Call Attempt Logged"
    FORM_SUBMISSION_COMPLETED = "FORM_SUBMISSION_COMPLETED", "Form Submission Completed"


class NotificationChannel(models.TextChoices):
    IN_APP = "IN_APP", "In App"
    EMAIL = "EMAIL", "Email"
    BOTH = "BOTH", "Both"


class NotificationTemplate(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    event_type = models.CharField(max_length=100, db_index=True)
    message = models.TextField()
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.IN_APP,
    )
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_template"
        ordering = ["event_type", "-is_default", "-created_at"]

        permissions = [
            ("manage_notification_template", "Can manage notification template"),
        ]

    def save(self, *args, **kwargs):
        # If set as default for this event type, set is_default=False for other templates of the same event_type
        if self.is_default:
            NotificationTemplate.objects.filter(
                event_type=self.event_type,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.event_type})"


class Notification(models.Model):
    id = models.AutoField(primary_key=True)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="notifications",
    )
    event_type = models.CharField(max_length=100, db_index=True)
    message = models.TextField()
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.IN_APP,
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification"
        ordering = ["-created_at"]

        permissions = [
            ("send_manual_notification", "Can send manual notification"),
        ]

    def __str__(self):
        return f"Notification to {self.recipient} - {self.event_type}"
