from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class QuotationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
    APPROVED = "APPROVED", "Approved"
    SENT = "SENT", "Sent"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    REVISION_REQUESTED = "REVISION_REQUESTED", "Revision Requested"
    REVISED = "REVISED", "Revised"


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
    # The funnel shape is defined dynamically by its PipelineStages; this
    # free-text label lets managers name the engagement type ("Project",
    # "Product Order", "Ticket", ...) without a fixed taxonomy.
    entity_label = models.CharField(
        max_length=100,
        default="Deal",
        help_text="Custom label for engagement items in this pipeline (e.g. 'Project', 'Product Order', 'Ticket').",
    )
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


class CustomerAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    company_name = models.CharField(max_length=255, db_index=True)
    gst_number = models.CharField(
        max_length=50, blank=True, null=True, unique=True, db_index=True
    )
    website = models.URLField(blank=True, null=True)
    primary_phone = models.CharField(max_length=20, blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_customer_accounts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customer_account"
        ordering = ["company_name"]
        permissions = [
            ("manage_customer_account", "Can manage customer account"),
        ]

    def __str__(self):
        return (
            f"{self.company_name} ({self.gst_number})"
            if self.gst_number
            else self.company_name
        )


class CustomerContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    account = models.ForeignKey(
        CustomerAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customer_contact"
        ordering = ["name"]
        permissions = [
            ("manage_customer_contact", "Can manage customer contact"),
        ]

    def __str__(self):
        return f"{self.name} - {self.email or self.phone}"


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

    # Dynamic quotation workflow configuration.
    # When `requires_quotation` is True, Leads sitting on this stage must go
    # through the quotation workflow before they can move on / be converted.
    # `quotation_approval_required` makes quotation revisions require manager
    # approval before they can be sent.
    requires_quotation = models.BooleanField(default=False)
    quotation_approval_required = models.BooleanField(default=False)

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

    class FinancialStatus(models.TextChoices):
        NO_DUES = "NO_DUES", "No Outstanding Dues"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAYMENT_OVERDUE = "PAYMENT_OVERDUE", "Payment Overdue"

    customer_account = models.ForeignKey(
        CustomerAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    customer_contact = models.ForeignKey(
        CustomerContact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )

    financial_status = models.CharField(
        max_length=20,
        choices=FinancialStatus.choices,
        default=FinancialStatus.NO_DUES,
    )
    total_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    paid_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    due_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    metadata = models.JSONField(default=dict, blank=True)

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
        indexes = [
            models.Index(
                fields=["assigned_to", "status"], name="lead_assigned_status_idx"
            ),
            models.Index(
                fields=["pipeline", "current_stage"], name="lead_pipeline_stage_idx"
            ),
            models.Index(fields=["created_at"], name="lead_created_at_idx"),
        ]

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
                errors["lost_reason"] = "Lost reason is required when a Lead is lost."

            if not self.lost_at:
                errors["lost_at"] = "Lost timestamp is required when a Lead is lost."

        # Non-lost Leads should not contain lost metadata.
        if self.status != self.Status.LOST:
            if self.lost_reason:
                errors["lost_reason"] = "Lost reason can only be set for a lost Lead."

            if self.lost_at:
                errors["lost_at"] = "Lost timestamp can only be set for a lost Lead."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    lead = models.OneToOneField(
        Lead,
        on_delete=models.SET_NULL,
        related_name="customer",
        null=True,
        blank=True,
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
        constraints = [
            models.UniqueConstraint(fields=["email"], name="uq_customer_email"),
            models.UniqueConstraint(fields=["phone"], name="uq_customer_phone"),
        ]

    def __str__(self):
        return self.name


class Quotation(models.Model):
    """
    Logical quotation document. A Quotation holds a reference number and points
    at its `current_version`. Every revision creates a new QuotationVersion
    instead of overwriting the previous one, so the full history is preserved.
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    quotation_number = models.CharField(max_length=50, unique=True)

    lead = models.ForeignKey(
        Lead,
        on_delete=models.PROTECT,
        related_name="quotations",
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="quotations",
        blank=True,
        null=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_quotations",
    )

    current_version = models.ForeignKey(
        "QuotationVersion",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )

    accepted_version = models.ForeignKey(
        "QuotationVersion",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )

    # Mirrors the current version's status so clients can read the active
    # quotation state without traversing versions. Kept in sync by the service.
    status = models.CharField(
        max_length=30,
        choices=QuotationStatus.choices,
        default=QuotationStatus.DRAFT,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quotation"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead", "status"], name="quotation_lead_status_idx"),
            models.Index(fields=["created_at"], name="quotation_created_at_idx"),
        ]

        permissions = [
            ("submit_quotation", "Can submit quotation for approval"),
            ("approve_quotation", "Can approve quotation"),
            ("approve_own_quotation", "Can approve own quotation"),
            ("send_quotation", "Can send quotation"),
            ("accept_quotation", "Can accept quotation"),
            ("reject_quotation", "Can reject quotation"),
            ("request_quotation_revision", "Can request quotation revision"),
            ("generate_quotation_pdf", "Can generate quotation PDF"),
        ]

    def __str__(self):
        return self.quotation_number


class QuotationVersion(models.Model):
    """
    A single version of a Quotation. Status lives on the version so each
    revision carries its own lifecycle (DRAFT -> APPROVED -> SENT -> ...).
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name="versions",
    )

    version_number = models.PositiveIntegerField()

    status = models.CharField(
        max_length=30,
        choices=QuotationStatus.choices,
        default=QuotationStatus.DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_quotation_versions",
    )

    # Responsible agent. Kept decoupled from Member 3's Task assignment so
    # Member 3 can freely assign/reassign the follow-up Task.
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_quotation_versions",
    )

    # Pipeline/stage context snapshot taken at creation time.
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.PROTECT,
        related_name="quotation_versions",
        blank=True,
        null=True,
    )

    current_stage = models.ForeignKey(
        PipelineStage,
        on_delete=models.PROTECT,
        related_name="quotation_versions",
        blank=True,
        null=True,
    )

    # Snapshot of whether approval was required for this version so later
    # changes to the pipeline configuration cannot alter history.
    approval_required = models.BooleanField(default=False)

    total_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    terms = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    approved_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    sent_to = models.EmailField(blank=True, null=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    revision_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quotation_version"
        ordering = ["quotation", "version_number"]

        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "version_number"],
                name="unique_quotation_version",
            ),
        ]

    def __str__(self):
        return f"{self.quotation.quotation_number} v{self.version_number}"

    def clean(self):
        if self.pk:
            line_items_amount = sum(
                li.quantity * li.unit_price for li in self.line_items.all()
            )
            if self.total_amount != line_items_amount:
                raise ValidationError(
                    {
                        "total_amount": (
                            f"Total amount {self.total_amount} does not match "
                            f"calculated sum {line_items_amount} from line items."
                        )
                    }
                )


class QuotationLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    version = models.ForeignKey(
        QuotationVersion,
        on_delete=models.CASCADE,
        related_name="line_items",
    )

    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def amount(self):
        return self.quantity * self.unit_price

    class Meta:
        db_table = "quotation_line_item"
        ordering = ["version", "created_at"]

    def __str__(self):
        return self.description


class QuotationApproval(models.Model):
    class Decision(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    version = models.ForeignKey(
        QuotationVersion,
        on_delete=models.CASCADE,
        related_name="approvals",
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_quotation_approvals",
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_quotation_approvals",
        blank=True,
        null=True,
    )

    decision = models.CharField(
        max_length=20,
        choices=Decision.choices,
        default=Decision.PENDING,
    )

    reason = models.TextField(blank=True, null=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "quotation_approval"
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.version} - {self.decision}"


class QuotationIntegrationEvent(models.Model):
    """
    Member 2 -> Member 3 integration contract.

    Member 2 (CRM) never creates Tasks. Instead it records integration events
    such as `quotation.followup_required` that describe work that needs to be
    performed. Member 3's Task Management system consumes these events and
    creates/assigns its own Task records.

    Contract:
      * event_type: "quotation.followup_required"
      * payload contains: lead_id, customer_id, quotation_id,
        quotation_number, quotation_version, responsible_agent_id,
        suggested_task_title, suggested_due_date, source
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONSUMED = "CONSUMED", "Consumed"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    event_type = models.CharField(max_length=100)

    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        related_name="quotation_integration_events",
        blank=True,
        null=True,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        related_name="quotation_integration_events",
        blank=True,
        null=True,
    )

    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.SET_NULL,
        related_name="integration_events",
        blank=True,
        null=True,
    )

    quotation_version_number = models.PositiveIntegerField(blank=True, null=True)

    payload = models.JSONField(blank=True, default=dict)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quotation_integration_event"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} - {self.id}"
