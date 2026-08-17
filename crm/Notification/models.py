from django.db import models
from django.conf import settings


class NotificationEventType(models.TextChoices):
    # Task Events
    TASK_ASSIGNED = "TASK_ASSIGNED", "Task Assigned"
    TASK_COMPLETED = "TASK_COMPLETED", "Task Completed"
    TASK_UPDATED = "TASK_UPDATED", "Task Updated"
    TASK_REASSIGNED = "TASK_REASSIGNED", "Task Reassigned"
    TASK_REMINDER = "TASK_REMINDER", "Task Reminder"

    # FollowUp Events
    FOLLOWUP_CREATED = "FOLLOWUP_CREATED", "Follow-up Created"
    FOLLOWUP_COMPLETED = "FOLLOWUP_COMPLETED", "Follow-up Completed"
    FOLLOWUP_REMINDER = "FOLLOWUP_REMINDER", "Follow-up Reminder"

    # Quotation Events
    QUOTATION_SUBMITTED = "QUOTATION_SUBMITTED", "Quotation Submitted"
    QUOTATION_APPROVED = "QUOTATION_APPROVED", "Quotation Approved"
    QUOTATION_REJECTED = "QUOTATION_REJECTED", "Quotation Rejected"

    # Accounts / User Events
    ROLE_CHANGED = "ROLE_CHANGED", "Role Changed"
    USER_ASSIGNED = "USER_ASSIGNED", "User Assigned"

    # Manual / Other Events
    MANUAL = "MANUAL", "Manual Notification"


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
