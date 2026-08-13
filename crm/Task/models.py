from django.db import models
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
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="assigned_tasks"
    )

    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="created_tasks"
    )
    #Developer 2 - Lead
    lead = models.ForeignKey(
        "customer_management.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks"
    )
    # Developer 2 - Customer
    customer = models.ForeignKey(
        "customer_management.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks"
    )
    task_title = models.CharField(max_length=200)
    description = models.TextField(
        blank=True,
        null=True
    )
    due_date = models.DateTimeField(
        blank=True,
        null=True
    )
    status = models.ForeignKey(
        TaskStatus,
        on_delete=models.PROTECT,
        related_name="tasks"
    )
    priority = models.ForeignKey(
        TaskPriority,
        on_delete=models.PROTECT,
        related_name="tasks"
    )
    category = models.ForeignKey(
        TaskCategory,
        on_delete=models.PROTECT,
        related_name="tasks"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.task_title

    class Meta:
        permissions = [
            ("assign_task", "Can assign task"),
        ]
    
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
    meeting_id = models.AutoField(primary_key=True)

    # Task relationship
    task_id = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="meetings"
    )

    # Meeting Status
    meeting_status_id = models.ForeignKey(
        MeetingStatus,
        on_delete=models.PROTECT,
        related_name="meetings"
    )

    # Meeting Type
    meeting_type_id = models.ForeignKey(
        MeetingType,
        on_delete=models.PROTECT,
        related_name="meetings"
    )

    meeting_title = models.CharField(max_length=100)
    meeting_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    description = models.TextField(
        blank=True,
        null=True
    )
    # Developer 1 - User
    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="created_meetings"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.meeting_title

class MeetingParticipant(models.Model):
    participant_id = models.AutoField(primary_key=True)
    # Meeting relationship
    meeting_id = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="participants"
    )
    # Developer 1 - User
    user_id = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="meeting_participations"
    )
    participant_role = models.CharField(max_length=100)
    is_required = models.BooleanField(default=True)


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
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reminders"
    )

    # Meeting relationship
    meeting_id = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reminders"
    )
    # Reminder Type
    reminder_type_id = models.ForeignKey(
        ReminderType,
        on_delete=models.PROTECT,
        related_name="reminders"
    )

    # Reminder Status
    reminder_status_id = models.ForeignKey(
        ReminderStatus,
        on_delete=models.PROTECT,
        related_name="reminders"
    )

    reminder_datetime = models.DateTimeField()
    message = models.TextField()
    # Developer 1 - User
    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="created_reminders"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)