from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class LeadSource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_lead_sources",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lead_source"
        ordering = ["name"]

        permissions = [
            ("manage_lead_source", "Can manage lead source"),
        ]

    def __str__(self):
        return self.name


class Pipeline(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_pipelines",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pipeline"
        ordering = ["name"]

        permissions = [
            ("manage_pipeline", "Can manage pipeline"),
        ]

    def __str__(self):
        return self.name


class PipelineStage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.PROTECT,
        related_name="stages",
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    display_order = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pipeline_stage"
        ordering = ["pipeline", "display_order"]

        constraints = [
            models.UniqueConstraint(
                fields=["pipeline", "name"],
                name="unique_pipeline_stage_name",
            ),
            models.UniqueConstraint(
                fields=["pipeline", "display_order"],
                name="unique_pipeline_stage_order",
            ),
        ]

        permissions = [
            ("manage_pipeline_stage", "Can manage pipeline stage"),
        ]

    def __str__(self):
        return f"{self.pipeline.name} - {self.name}"


class Lead(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        LOST = "LOST", "Lost"
        CONVERTED = "CONVERTED", "Converted"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)

    source = models.ForeignKey(
        LeadSource,
        on_delete=models.PROTECT,
        related_name="leads",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_leads",
    )

    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.PROTECT,
        related_name="leads",
    )

    current_stage = models.ForeignKey(
        PipelineStage,
        on_delete=models.PROTECT,
        related_name="leads",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    lost_reason = models.TextField(blank=True, null=True)
    lost_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lead"
        ordering = ["-created_at"]

        permissions = [
            ("assign_lead", "Can assign lead"),
            ("progress_lead", "Can progress lead"),
            ("mark_lead_lost", "Can mark lead as lost"),
            ("reengage_lead", "Can re-engage lead"),
            ("convert_lead", "Can convert lead to customer"),
        ]

    def clean(self):
        errors = {}

        # Pipeline and current stage must match.
        if self.pipeline_id and self.current_stage_id:
            if self.current_stage.pipeline_id != self.pipeline_id:
                errors["current_stage"] = (
                    "The selected stage does not belong to the selected pipeline."
                )

        # Lost Lead validation.
        if self.status == self.Status.LOST:
            if not self.lost_reason:
                errors["lost_reason"] = (
                    "Lost reason is required when a Lead is lost."
                )

            if not self.lost_at:
                errors["lost_at"] = (
                    "Lost timestamp is required when a Lead is lost."
                )

        # Non-lost Leads should not contain lost metadata.
        if self.status != self.Status.LOST:
            if self.lost_reason:
                errors["lost_reason"] = (
                    "Lost reason can only be set for a lost Lead."
                )

            if self.lost_at:
                errors["lost_at"] = (
                    "Lost timestamp can only be set for a lost Lead."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    lead = models.OneToOneField(
        Lead,
        on_delete=models.PROTECT,
        related_name="customer",
    )

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    company_name = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customer"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Activity(models.Model):

    class ActivityType(models.TextChoices):
        CALL = "CALL", "Call"
        EMAIL = "EMAIL", "Email"
        MEETING = "MEETING", "Meeting"
        DEMO = "DEMO", "Demo"
        FOLLOW_UP = "FOLLOW_UP", "Follow Up"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    lead = models.ForeignKey(
        Lead,
        on_delete=models.PROTECT,
        related_name="activities",
        blank=True,
        null=True,
    )

    customer = models.ForeignKey(
        Customer,
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


class AuditLog(models.Model):
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
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - {self.entity_type}"