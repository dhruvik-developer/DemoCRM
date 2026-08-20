from django.db import models

# Create your models here.
# ==============================================================================
#                                   FOLLOWUPS API
# ==============================================================================
# followup_status
class FollowUpStatus(models.Model):
    followup_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.status_name


# followup_type
class FollowUpTypes(models.Model):
    followup_type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.type_name


class Followup(models.Model):
    followup_id = models.AutoField(primary_key=True)
    task_id = models.ForeignKey(
        "Task.Task", on_delete=models.CASCADE, related_name="followups"
    )
    followup_status = models.ForeignKey(
        FollowUpStatus, on_delete=models.PROTECT, related_name="followups"
    )
    followup_type = models.ForeignKey(
        FollowUpTypes, on_delete=models.PROTECT, related_name="followups"
    )
    followup_date = models.DateTimeField()
    decription = models.TextField(blank=True, null=True)
    # Developer 1 - User
    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="created_followups",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ==============================================================================
#                                    ACTIVITY LOG API
# ==============================================================================
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
        "accounts.CustomUser", on_delete=models.PROTECT, related_name="activity_logs"
    )
    activity_type_id = models.ForeignKey(
        ActivityType, on_delete=models.PROTECT, related_name="activity_logs"
    )
    activity_action_id = models.ForeignKey(
        ActivityAction, on_delete=models.PROTECT, related_name="activity_logs"
    )
    description = models.TextField(blank=True, null=True)
    reference_id = models.PositiveIntegerField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
