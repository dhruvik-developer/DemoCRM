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
    is_active = models.BooleanField(default=True)
    # Developer 1 - User
    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="created_followups",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

