from django.db import models

# Create your models here.
#==============================================================================
#                                   FOLLOWUPS API
#==============================================================================
#followup_status
class FollowUpStatus(models.Model):
    followup_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.status_name
#followup_type
class FollowUpTypes(models.Model):
    followup_type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.type_name

class Followup(models.Model):
    followup_id = models.AutoField(primary_key=True)
    task_id = models.ForeignKey("Task.Task",on_delete=models.CASCADE,related_name="followups")
    followup_status = models.ForeignKey(FollowUpStatus,on_delete=models.PROTECT,related_name="followups")
    followup_type = models.ForeignKey(FollowUpTypes,on_delete=models.PROTECT, related_name="followups")
    followup_date = models.DateTimeField()
    decription = models.TextField(blank=True,null=True)
    # Developer 1 - User
    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="created_followups"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
#follow_up_note 
class FollowUpNote(models.Model):
    note_id = models.AutoField(primary_key=True)
    followup_id = models.ForeignKey(Followup, on_delete=models.CASCADE, related_name="notes")
    #developer 1
    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="created_followup_notes"
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

#==============================================================================
#                                    ACTIVITY LOG API
#==============================================================================
class ActivityType(models.Model):
    activity_type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

class ActivityAction(models.Model):
    activity_action_id = models.AutoField(primary_key=True)
    action_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

class ActivityLog(models.Model):
    activity_id = models.AutoField(primary_key=True)
    # Developer 1 - Custom User
    user_id = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="activity_logs"
    )
    activity_type_id = models.ForeignKey(ActivityType, on_delete=models.PROTECT, related_name="activity_logs")
    activity_action_id = models.ForeignKey(ActivityAction,on_delete=models.PROTECT,related_name="activity_logs")
    description = models.TextField(blank=True, null=True)
    reference_id = models.PositiveIntegerField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

 #==============================================================================
#                                    NOTIFICATION API
#==============================================================================
class NotificationType(models.Model):
    notification_type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

class NotificationTemplate(models.Model):
    template_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, blank=True, default="")
    notification_type_id = models.ForeignKey(
        NotificationType,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="templates",
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_active = models.BooleanField(default=True)

class Notification(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SCHEDULED = "SCHEDULED", "Scheduled"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    notification_id = models.AutoField(primary_key=True)
    # Developer 1 - User
    user_id = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="notifications"
    )  
    notification_type_id = models.ForeignKey(NotificationType, on_delete=models.PROTECT, related_name="notifications")
    template_id = models.ForeignKey(NotificationTemplate, on_delete=models.PROTECT, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    is_customized = models.BooleanField(default=False)
    # Developer 1 - User
    edited_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="edited_notifications",
    )
    scheduled_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("send_notification", "Can send notification"),
        ]
