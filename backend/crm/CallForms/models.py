from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# ======================================================
# CALL TEMPLATE & VERSIONING
# ======================================================


class CallTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_call_templates",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "call_template"
        ordering = ["name"]
        permissions = [
            ("manage_call_template", "Can manage call template"),
        ]

    def __str__(self):
        return self.name


class TemplateVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    template = models.ForeignKey(
        CallTemplate,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    version_label = models.CharField(max_length=50, blank=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_template_versions",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "template_version"
        ordering = ["template", "-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "version_number"],
                name="unique_template_version_number",
            ),
        ]
        permissions = [
            ("manage_template_version", "Can manage template version"),
        ]

    @property
    def is_locked(self):
        """A version is locked once it has been used by a FormSubmission."""
        return self.submissions.exists()

    def clean(self):
        if self.pk and self.is_locked:
            raise ValidationError(
                "This template version has existing form submissions and cannot be modified. Create a new version instead."
            )

    def save(self, *args, **kwargs):
        if not self.version_label:
            self.version_label = f"v{self.version_number}.0"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.template.name} - {self.version_label or self.version_number}"


class FieldType(models.TextChoices):
    TEXT = "text", "Text"
    TEXTAREA = "textarea", "Text Area"
    NUMBER = "number", "Number"
    BOOLEAN = "boolean", "Boolean"
    DATE = "date", "Date"
    TIME = "time", "Time"
    DATETIME = "datetime", "Date & Time"
    SELECT = "select", "Select"
    RADIO = "radio", "Radio"
    CHECKBOX = "checkbox", "Checkbox"
    FILE = "file", "File Upload"


class TemplateField(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    template_version = models.ForeignKey(
        TemplateVersion,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    field_key = models.CharField(max_length=100)
    label = models.CharField(max_length=200)
    field_type = models.CharField(
        max_length=20,
        choices=FieldType.choices,
        default=FieldType.TEXT,
    )
    is_required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=1)
    help_text = models.TextField(blank=True, null=True)
    options = models.JSONField(default=list, blank=True)
    validation_rules = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "template_field"
        ordering = ["template_version", "display_order", "field_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["template_version", "field_key"],
                name="unique_template_field_key",
            ),
        ]
        permissions = [
            ("manage_template_field", "Can manage template field"),
        ]

    def clean(self):
        if self.template_version and self.template_version.is_locked:
            raise ValidationError(
                "Cannot add or modify fields on a locked template version."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.template_version} -> {self.label} ({self.field_key})"


class FormFieldMapping(models.Model):
    """Admin-configurable mapping from template field_key to Lead/Customer target field."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    template = models.ForeignKey(
        CallTemplate, on_delete=models.CASCADE, related_name="field_mappings"
    )
    field_key = models.CharField(max_length=100)
    target_model = models.CharField(
        max_length=30,
        choices=[
            ("Lead", "Lead"),
            ("Customer", "Customer"),
            ("CustomerAccount", "CustomerAccount"),
        ],
        default="Lead",
    )
    target_field = models.CharField(
        max_length=100,
        help_text="e.g. gst_number, company_name, metadata.annual_revenue",
    )

    class Meta:
        db_table = "form_field_mapping"
        unique_together = [("template", "field_key")]
        ordering = ["template", "field_key"]

    def __str__(self):
        return f"{self.template.name}:{self.field_key} -> {self.target_model}.{self.target_field}"


# ======================================================
# PIPELINE STAGE ACTIVITY
# ======================================================


class ActivityType(models.TextChoices):
    CALL = "CALL", "Call"
    MEETING = "MEETING", "Meeting"
    EMAIL = "EMAIL", "Email"
    FOLLOWUP = "FOLLOWUP", "Follow-up"


class PipelineStageActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    stage = models.ForeignKey(
        "customer_management.PipelineStage",
        on_delete=models.CASCADE,
        related_name="activities",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    activity_type = models.CharField(
        max_length=50,
        choices=ActivityType.choices,
        default=ActivityType.CALL,
    )
    call_template = models.ForeignKey(
        CallTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stage_activities",
    )
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    # Role-based visibility: which roles may see/fill this form.
    # Empty list = visible to all authenticated users.
    allowed_roles = models.JSONField(default=list, blank=True)
    # Who may submit/edit (subset of allowed_roles). Empty = same as allowed_roles.
    editable_roles = models.JSONField(default=list, blank=True)
    # Form type for multi-form per stage tabs: CALL | PROPOSAL | OFFER | CONTRACT | CUSTOM
    form_type = models.CharField(
        max_length=20,
        choices=[
            ("CALL", "Call"),
            ("PROPOSAL", "Proposal"),
            ("OFFER", "Offer"),
            ("CONTRACT", "Contract"),
            ("CUSTOM", "Custom"),
        ],
        default="CALL",
    )
    # Per-stage form config: auto_create_followup for NO_ANSWER/BUSY/CALLBACK
    auto_create_followup = models.BooleanField(default=True)
    followup_offset_days = models.PositiveIntegerField(default=1)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_stage_activities",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pipeline_stage_activity"
        ordering = ["stage", "display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["stage", "name"],
                name="unique_stage_activity_name",
            ),
        ]
        permissions = [
            ("manage_stage_activity", "Can manage stage activity"),
            ("manage_pipeline_stage_form", "Can manage pipeline stage form"),
        ]

    def __str__(self):
        return f"{self.stage.name} - {self.name}"


# ======================================================
# CALL ATTEMPT & FORM SUBMISSION
# ======================================================


class OutcomeChoice(models.TextChoices):
    NO_ANSWER = "NO_ANSWER", "No Answer"
    BUSY = "BUSY", "Busy"
    CONNECTED = "CONNECTED", "Connected"
    CALLBACK = "CALLBACK", "Callback Scheduled"
    WRONG_NUMBER = "WRONG_NUMBER", "Wrong Number"
    DO_NOT_CALL = "DO_NOT_CALL", "Do Not Call"
    COMPLETED = "COMPLETED", "Form Completed"
    LOST_SUGGESTED = "LOST_SUGGESTED", "Threshold Reached - Mark Lost Suggested"


class CallAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    lead = models.ForeignKey(
        "customer_management.Lead",
        on_delete=models.PROTECT,
        related_name="call_attempts",
    )
    stage = models.ForeignKey(
        "customer_management.PipelineStage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="call_attempts",
    )
    activity = models.ForeignKey(
        PipelineStageActivity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="call_attempts",
    )
    template_version = models.ForeignKey(
        TemplateVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="call_attempts",
    )
    attempt_number = models.PositiveIntegerField(default=1)

    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="conducted_call_attempts",
    )

    outcome = models.CharField(
        max_length=50,
        choices=OutcomeChoice.choices,
        default=OutcomeChoice.NO_ANSWER,
    )
    notes = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    is_form_submitted = models.BooleanField(default=False)
    # Set when consecutive failed attempts reach the configured threshold.
    # The real outcome is preserved untouched (attempt != business call).
    suggest_mark_lost = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "call_attempt"
        ordering = ["lead", "-attempt_number", "-created_at"]
        permissions = [
            ("can_create_followup", "Can create followup from call"),
        ]

    @property
    def duration_seconds(self):
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time).total_seconds())
        return None

    def __str__(self):
        return (
            f"Attempt #{self.attempt_number} for Lead {self.lead_id} ({self.outcome})"
        )


class FormSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    lead = models.ForeignKey(
        "customer_management.Lead",
        on_delete=models.PROTECT,
        related_name="form_submissions",
    )
    call_attempt = models.ForeignKey(
        CallAttempt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_submissions",
    )
    template_version = models.ForeignKey(
        TemplateVersion,
        on_delete=models.PROTECT,
        related_name="submissions",
    )
    quotation = models.ForeignKey(
        "customer_management.Quotation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_submissions",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="form_submissions",
    )
    data = models.JSONField(default=dict)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "form_submission"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Submission {self.id} for {self.template_version}"


class ConditionChoice(models.TextChoices):
    ALWAYS = "ALWAYS", "Always Trigger on Submission"
    FOLLOW_UP_REQUIRED = "FOLLOW_UP_REQUIRED", "When Follow-Up is Required"
    OUTCOME_MATCH = "OUTCOME_MATCH", "When Call Attempt Outcome Matches"
    FIELD_VALUE_MATCH = "FIELD_VALUE_MATCH", "When Specific Field Matches Value"


class AssigneeRuleChoice(models.TextChoices):
    CONDUCTING_AGENT = "CONDUCTING_AGENT", "Conducting Agent"
    LEAD_OWNER = "LEAD_OWNER", "Lead Assigned Owner"
    SPECIFIC_USER = "SPECIFIC_USER", "Specific User"


class TaskTriggerRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    template_version = models.ForeignKey(
        TemplateVersion,
        on_delete=models.CASCADE,
        related_name="trigger_rules",
    )
    name = models.CharField(max_length=150)
    trigger_condition = models.CharField(
        max_length=50,
        choices=ConditionChoice.choices,
        default=ConditionChoice.ALWAYS,
    )
    condition_field_key = models.CharField(max_length=100, blank=True, default="")
    condition_value = models.JSONField(default=dict, blank=True)

    task_title_template = models.CharField(
        max_length=200,
        default="Follow-up with {lead_name}",
        help_text="Title template supporting {lead_name}, {stage_name}, {template_name}",
    )
    task_category = models.ForeignKey(
        "Task.TaskCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="callform_trigger_rules",
    )
    task_priority = models.ForeignKey(
        "Task.TaskPriority",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="callform_trigger_rules",
    )
    due_days_offset = models.PositiveIntegerField(default=1)

    assignee_rule = models.CharField(
        max_length=50,
        choices=AssigneeRuleChoice.choices,
        default=AssigneeRuleChoice.CONDUCTING_AGENT,
    )
    specific_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="callform_assigned_rules",
    )

    create_reminder = models.BooleanField(default=True)
    reminder_minutes_before = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "task_trigger_rule"
        ordering = ["name"]

    def __str__(self):
        return f"TriggerRule '{self.name}' on {self.template_version}"


# ======================================================
# AD-HOC FIELD PROPOSAL
# ======================================================


class ProposalStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class AdhocFieldProposal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    template_version = models.ForeignKey(
        TemplateVersion,
        on_delete=models.CASCADE,
        related_name="adhoc_proposals",
    )
    field_key = models.CharField(max_length=100)
    label = models.CharField(max_length=200)
    field_type = models.CharField(
        max_length=20,
        choices=FieldType.choices,
        default=FieldType.TEXT,
    )
    help_text = models.TextField(blank=True, null=True)
    options = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ProposalStatus.choices,
        default=ProposalStatus.PENDING,
    )

    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="proposed_adhoc_fields",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_adhoc_fields",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "adhoc_field_proposal"
        ordering = ["-created_at"]
        permissions = [
            ("add_adhoc_field", "Can propose ad-hoc field"),
            ("manage_adhoc_field", "Can manage/review ad-hoc field proposal"),
        ]

    def __str__(self):
        return f"Proposal '{self.label}' ({self.field_key}) - {self.status}"


# ======================================================
# INDEXED SUBMISSION VALUE
# ======================================================


class IndexedSubmissionValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    submission = models.ForeignKey(
        FormSubmission,
        on_delete=models.CASCADE,
        related_name="indexed_values",
    )
    field_key = models.CharField(max_length=100, db_index=True)
    value_text = models.TextField(null=True, blank=True)
    value_number = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, db_index=True
    )
    value_date = models.DateField(null=True, blank=True, db_index=True)
    value_boolean = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "indexed_submission_value"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "field_key"],
                name="unique_submission_field_key_index",
            ),
        ]

    def __str__(self):
        return f"IndexedValue '{self.field_key}' for Submission {self.submission_id}"
