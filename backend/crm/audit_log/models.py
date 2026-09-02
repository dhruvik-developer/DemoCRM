from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditLog(models.Model):
    """
    Audit log for tracking CRM mutations.

    NOTE: `entity_id` is a UUIDField but some entities (Task, Meeting, Reminder,
    FollowUp) use integer AutoField PKs. When logging those entities, cast the
    int PK to a string UUID-compatible format or use a deterministic mapping.
    A future migration to CharField for `entity_id` is recommended for full
    compatibility.
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )

    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField()

    action = models.CharField(max_length=100)

    old_value = models.JSONField(blank=True, null=True)
    new_value = models.JSONField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        managed = False
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - {self.entity_type}"


class Activity(models.Model):
    class ActivityType(models.TextChoices):
        CALL = "CALL", "Call"
        EMAIL = "EMAIL", "Email"
        MEETING = "MEETING", "Meeting"
        DEMO = "DEMO", "Demo"
        FOLLOW_UP = "FOLLOW_UP", "Follow Up"
        QUOTATION_CREATED = "QUOTATION_CREATED", "Quotation Created"
        QUOTATION_UPDATED = "QUOTATION_UPDATED", "Quotation Updated"
        QUOTATION_SUBMITTED = "QUOTATION_SUBMITTED", "Quotation Submitted"
        QUOTATION_APPROVED = "QUOTATION_APPROVED", "Quotation Approved"
        QUOTATION_APPROVAL_REJECTED = (
            "QUOTATION_APPROVAL_REJECTED",
            "Quotation Approval Rejected",
        )
        QUOTATION_SENT = "QUOTATION_SENT", "Quotation Sent"
        QUOTATION_REVISION_REQUESTED = (
            "QUOTATION_REVISION_REQUESTED",
            "Quotation Revision Requested",
        )
        QUOTATION_VERSION_CREATED = (
            "QUOTATION_VERSION_CREATED",
            "Quotation Version Created",
        )
        QUOTATION_ACCEPTED = "QUOTATION_ACCEPTED", "Quotation Accepted"
        QUOTATION_REJECTED = "QUOTATION_REJECTED", "Quotation Rejected"
        QUOTATION_PDF_GENERATED = "QUOTATION_PDF_GENERATED", "Quotation PDF Generated"
        QUOTATION_EMAIL_SENT = "QUOTATION_EMAIL_SENT", "Quotation Email Sent"

        # Payment Events
        PAYMENT = "PAYMENT", "Payment"

        # Task Events
        TASK_CREATED = "TASK_CREATED", "Task Created"
        TASK_UPDATED = "TASK_UPDATED", "Task Updated"
        TASK_DELETED = "TASK_DELETED", "Task Deleted"
        TASK_ASSIGNED = "TASK_ASSIGNED", "Task Assigned"
        TASK_REASSIGNED = "TASK_REASSIGNED", "Task Reassigned"
        TASK_STATUS_CHANGED = "TASK_STATUS_CHANGED", "Task Status Changed"

        # FollowUp Events
        FOLLOWUP_CREATED = "FOLLOWUP_CREATED", "Follow-up Created"
        FOLLOWUP_UPDATED = "FOLLOWUP_UPDATED", "Follow-up Updated"
        FOLLOWUP_DELETED = "FOLLOWUP_DELETED", "Follow-up Deleted"

        # Reminder Events
        REMINDER_CREATED = "REMINDER_CREATED", "Reminder Created"
        REMINDER_UPDATED = "REMINDER_UPDATED", "Reminder Updated"
        REMINDER_DELETED = "REMINDER_DELETED", "Reminder Deleted"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    lead = models.ForeignKey(
        "customer_management.Lead",
        on_delete=models.PROTECT,
        related_name="activities",
        blank=True,
        null=True,
    )

    customer = models.ForeignKey(
        "customer_management.Customer",
        on_delete=models.PROTECT,
        related_name="activities",
        blank=True,
        null=True,
    )

    quotation = models.ForeignKey(
        "customer_management.Quotation",
        on_delete=models.PROTECT,
        related_name="activities",
        blank=True,
        null=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="activities",
    )

    activity_type = models.CharField(
        max_length=30,
        choices=ActivityType.choices,
    )

    outcome = models.CharField(max_length=255)
    notes = models.TextField(blank=True, null=True)

    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "activity"
        managed = False
        ordering = ["-created_at"]

    def clean(self):
        if not self.lead_id and not self.customer_id:
            raise ValidationError(
                "An Activity must belong to either a Lead or a Customer."
            )

        if self.lead_id and self.customer_id:
            raise ValidationError(
                "An Activity cannot belong to both a Lead and a Customer."
            )

        if self.lead_id:
            from customer_management.models import Lead

            lead_status = (
                Lead.objects.filter(pk=self.lead_id)
                .values_list("status", flat=True)
                .first()
            )
            if lead_status == Lead.Status.CONVERTED:
                raise ValidationError(
                    "An Activity cannot be created against a CONVERTED Lead. Use the Customer instead."
                )

        if self.follow_up_required and not self.follow_up_date:
            raise ValidationError(
                "Follow-up date is required when follow-up is required."
            )

        if not self.follow_up_required and self.follow_up_date:
            raise ValidationError(
                "Follow-up date cannot be set when follow-up is not required."
            )

    def __str__(self):
        return f"{self.activity_type} - {self.outcome}"
