from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings

# ======================================================
# TASK
# ======================================================


class TaskStatus(models.Model):
    status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.status_name


class TaskPriority(models.Model):
    priority_id = models.AutoField(primary_key=True)
    priority_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.priority_name


class TaskCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.category_name


class Task(models.Model):
    task_id = models.AutoField(primary_key=True)
    # Developer 1 - User
    assigned_to = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.PROTECT, related_name="assigned_tasks"
    )

    created_by = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.PROTECT, related_name="created_tasks"
    )
    # Developer 2 - Lead
    lead = models.ForeignKey(
        "customer_management.Lead", on_delete=models.PROTECT, related_name="tasks"
    )
    # Developer 2 - Customer
    customer = models.ForeignKey(
        "customer_management.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    form_submission = models.ForeignKey(
        "CallForms.FormSubmission",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    task_title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField(blank=True, null=True)
    status = models.ForeignKey(
        TaskStatus, on_delete=models.PROTECT, related_name="tasks"
    )
    priority = models.ForeignKey(
        TaskPriority, on_delete=models.PROTECT, related_name="tasks"
    )
    category = models.ForeignKey(
        TaskCategory, on_delete=models.PROTECT, related_name="tasks"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.customer and self.lead:
            if self.customer.lead_id != self.lead_id:
                raise ValidationError("Customer must belong to the assigned Lead.")

    def __str__(self):
        return self.task_title


# ======================================================
# MEETING
# ======================================================


class MeetingStatus(models.Model):
    meeting_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.status_name


class MeetingType(models.Model):
    meeting_type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.type_name


class Meeting(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Manager Approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    meeting_id = models.AutoField(primary_key=True)

    # Task relationship
    task_id = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="meetings")

    # ==================================================
    # LEAD RELATIONSHIP
    # ==================================================

    lead = models.ForeignKey(
        "customer_management.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meetings",
    )

    # ==================================================
    # MEETING STATUS
    # ==================================================

    meeting_status_id = models.ForeignKey(
        MeetingStatus, on_delete=models.PROTECT, related_name="meetings"
    )

    # Meeting Type
    meeting_type_id = models.ForeignKey(
        MeetingType, on_delete=models.PROTECT, related_name="meetings"
    )

    meeting_title = models.CharField(max_length=100)
    meeting_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    # meeting link when meeting is a online : manager approve then send the customer
    meeting_link = models.URLField(blank=True, null=True)
    # Developer 1 - User
    created_by = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.PROTECT, related_name="created_meetings"
    )
    # manager
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="managed_meetings",
    )
    # manager approval
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    approved_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_meeting",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    extra_fields = models.JSONField(
        default=dict, blank=True, help_text="Custom dynamic fields added by employee"
    )

    def clean(self):
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError("End time must be after start time.")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["task_id", "meeting_date", "start_time"],
                name="uq_meeting_task_date_time",
            ),
        ]

    def __str__(self):
        return self.meeting_title


class MeetingParticipant(models.Model):
    participant_id = models.AutoField(primary_key=True)
    # Meeting relationship
    meeting_id = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, related_name="participants"
    )
    # Developer 1 - User
    user_id = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="meeting_participations",
    )
    participant_role = models.CharField(max_length=100)
    is_required = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["meeting_id", "user_id"],
                name="uq_meeting_participant",
            ),
        ]


# ======================================================
# REMINDER
# ======================================================


class ReminderType(models.Model):
    reminder_type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.type_name


class ReminderStatus(models.Model):
    reminder_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.status_name


class Reminder(models.Model):
    reminder_id = models.AutoField(primary_key=True)
    # Task relationship
    task_id = models.ForeignKey(
        Task, on_delete=models.CASCADE, null=True, blank=True, related_name="reminders"
    )

    # Meeting relationship
    meeting_id = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reminders",
    )
    reminder_for = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_reminders",
    )
    # Reminder Type
    reminder_type_id = models.ForeignKey(
        ReminderType, on_delete=models.PROTECT, related_name="reminders"
    )

    # Reminder Status
    reminder_status_id = models.ForeignKey(
        ReminderStatus, on_delete=models.PROTECT, related_name="reminders"
    )

    reminder_datetime = models.DateTimeField()
    message = models.TextField()
    is_sent = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    # Developer 1 - User
    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="created_reminders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if not self.task_id and not self.meeting_id:
            raise ValidationError("Reminder must be linked to either a Task or a Meeting.")

    def __str__(self):
        return f"Reminder {self.reminder_id}: {self.message[:30]}"
