from decimal import Decimal

from rest_framework import serializers
from django.core.validators import RegexValidator

from audit_log.models import Activity, AuditLog

from .models import (
    Customer,
    CustomerAccount,
    CustomerContact,
    Lead,
    LeadSource,
    Payment,
    Pipeline,
    PipelineStage,
    Quotation,
    QuotationApproval,
    QuotationIntegrationEvent,
    QuotationLineItem,
    QuotationVersion,
)


class CustomerAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAccount
        fields = [
            "id",
            "company_name",
            "gst_number",
            "website",
            "primary_phone",
            "billing_address",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class CustomerContactSerializer(serializers.ModelSerializer):
    account_detail = CustomerAccountSerializer(source="account", read_only=True)

    class Meta:
        model = CustomerContact
        fields = [
            "id",
            "account",
            "account_detail",
            "name",
            "email",
            "phone",
            "designation",
            "is_primary",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
        ]


class PipelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pipeline
        fields = [
            "id",
            "name",
            "description",
            "entity_label",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
        ]


class PipelineStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineStage
        fields = [
            "id",
            "pipeline",
            "name",
            "description",
            "display_order",
            "is_active",
            "requires_quotation",
            "quotation_approval_required",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        pipeline = attrs.get("pipeline")

        if pipeline and not pipeline.is_active:
            raise serializers.ValidationError(
                {"pipeline": "Cannot use an inactive pipeline."}
            )

        display_order = attrs.get("display_order")

        if display_order is not None and display_order < 1:
            raise serializers.ValidationError(
                {"display_order": "Display order must be at least 1."}
            )

        return attrs


class LeadSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        validators=[
            RegexValidator(
                regex=r"^[0-9+\-()\s]{7,20}$",
                message="Phone number must be 7-20 characters and contain only digits, +, -, (, ), or spaces.",
            )
        ],
    )

    class Meta:
        model = Lead
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "company_name",
            "customer_account",
            "customer_contact",
            "source",
            "assigned_to",
            "pipeline",
            "current_stage",
            "status",
            "financial_status",
            "total_value",
            "paid_amount",
            "due_amount",
            "metadata",
            "lost_reason",
            "lost_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "lost_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        source = attrs.get("source")
        pipeline = attrs.get("pipeline")
        current_stage = attrs.get("current_stage")
        assigned_to = attrs.get("assigned_to")

        if source and not source.is_active:
            raise serializers.ValidationError(
                {"source": "Cannot use an inactive lead source."}
            )

        if pipeline and not pipeline.is_active:
            raise serializers.ValidationError(
                {"pipeline": "Cannot use an inactive pipeline."}
            )

        target_pipeline_id = (
            pipeline.id
            if pipeline
            else (self.instance.pipeline_id if self.instance else None)
        )

        if current_stage:
            if not current_stage.is_active:
                raise serializers.ValidationError(
                    {"current_stage": "Cannot use an inactive stage."}
                )

            if target_pipeline_id and current_stage.pipeline_id != target_pipeline_id:
                raise serializers.ValidationError(
                    {
                        "current_stage": (
                            "The selected stage does not belong "
                            "to the selected pipeline."
                        )
                    }
                )

        if assigned_to and not assigned_to.is_active:
            raise serializers.ValidationError(
                {"assigned_to": ("An inactive employee cannot be assigned a Lead.")}
            )

        # A Lead that is LOST or CONVERTED is in a terminal state. State
        # transitions must go through the dedicated workflow endpoints
        # (progress / lost / re-engage / convert / assign). Direct PATCH/PUT
        # must be rejected so a converted Lead cannot keep behaving like an
        # active one.
        if self.instance and self.instance.status != Lead.Status.ACTIVE:
            raise serializers.ValidationError(
                {
                    "status": (
                        "A Lead that is not Active cannot be modified directly. "
                        "Use the workflow endpoints (assign/progress/lost/"
                        "re-engage/convert)."
                    )
                }
            )

        # lost_reason / lost_at may only be present on a LOST Lead. Since
        # status is read-only, it can never be set to LOST through a PATCH,
        # so any attempt to set lost_reason on a non-lost Lead is invalid.
        if "lost_reason" in attrs and (
            self.instance is None or self.instance.status != Lead.Status.LOST
        ):
            raise serializers.ValidationError(
                {"lost_reason": "Lost reason can only be set on a lost Lead."}
            )

        return attrs


class CustomerSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(
        validators=[
            RegexValidator(
                regex=r"^[0-9+\-()\s]{7,20}$",
                message="Phone number must be 7-20 characters and contain only digits, +, -, (, ), or spaces.",
            )
        ]
    )

    class Meta:
        model = Customer
        fields = [
            "id",
            "lead",
            "name",
            "email",
            "phone",
            "company_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        lead = attrs.get("lead")
        if lead and lead.status != "CONVERTED":
            raise serializers.ValidationError(
                {"lead": "Customer can only be created from a CONVERTED Lead."}
            )
        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "lead",
            "customer",
            "amount",
            "payment_date",
            "method",
            "reference",
            "notes",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_at"]

    def validate_amount(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = [
            "id",
            "lead",
            "customer",
            "created_by",
            "activity_type",
            "outcome",
            "notes",
            "follow_up_required",
            "follow_up_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        lead = attrs.get("lead")
        customer = attrs.get("customer")
        follow_up_required = attrs.get("follow_up_required")
        follow_up_date = attrs.get("follow_up_date")

        # Activity must belong to either Lead or Customer
        if not lead and not customer:
            raise serializers.ValidationError(
                "Activity must belong to a Lead or Customer."
            )

        if lead and customer:
            raise serializers.ValidationError(
                "Activity cannot belong to both a Lead and a Customer."
            )

        # Converted Leads cannot receive new activities
        if lead and lead.status == Lead.Status.CONVERTED:
            raise serializers.ValidationError(
                {
                    "lead": (
                        "Cannot create a new Activity for a converted Lead. "
                        "Create the Activity against the Customer instead."
                    )
                }
            )

        # Follow-up validation
        if follow_up_required and not follow_up_date:
            raise serializers.ValidationError(
                {
                    "follow_up_date": (
                        "Follow-up date is required when follow-up is required."
                    )
                }
            )

        if not follow_up_required and follow_up_date:
            raise serializers.ValidationError(
                {
                    "follow_up_date": (
                        "Follow-up date cannot be set when follow-up is not required."
                    )
                }
            )

        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "entity_type",
            "entity_id",
            "action",
            "old_value",
            "new_value",
            "metadata",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "entity_type",
            "entity_id",
            "action",
            "old_value",
            "new_value",
            "metadata",
            "created_at",
        ]


class QuotationLineItemSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = QuotationLineItem
        fields = [
            "id",
            "description",
            "hsn_code",
            "quantity",
            "unit_price",
            "gst_rate",
            "discount_percent",
            "amount",
            "created_at",
        ]
        read_only_fields = ["id", "amount", "created_at"]


class QuotationApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationApproval
        fields = [
            "id",
            "version",
            "submitted_by",
            "reviewed_by",
            "decision",
            "reason",
            "submitted_at",
            "reviewed_at",
        ]
        read_only_fields = [
            "id",
            "version",
            "submitted_by",
            "reviewed_by",
            "decision",
            "submitted_at",
            "reviewed_at",
        ]


class QuotationVersionSerializer(serializers.ModelSerializer):
    line_items = QuotationLineItemSerializer(many=True, read_only=True)
    approvals = QuotationApprovalSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    discount_amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True
    )
    gst_amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True
    )

    class Meta:
        model = QuotationVersion
        fields = [
            "id",
            "quotation",
            "version_number",
            "status",
            "created_by",
            "assigned_to",
            "pipeline",
            "current_stage",
            "approval_required",
            "subtotal_amount",
            "discount_type",
            "discount_value",
            "discount_amount",
            "gst_rate",
            "gst_amount",
            "subtotal",
            "total_amount",
            "terms",
            "notes",
            "line_items",
            "approvals",
            "approved_at",
            "sent_at",
            "sent_to",
            "accepted_at",
            "rejected_at",
            "rejection_reason",
            "revision_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "quotation",
            "version_number",
            "status",
            "created_by",
            "assigned_to",
            "pipeline",
            "current_stage",
            "approval_required",
            "subtotal_amount",
            "discount_amount",
            "gst_amount",
            "subtotal",
            "total_amount",
            "line_items",
            "approvals",
            "approved_at",
            "sent_at",
            "sent_to",
            "accepted_at",
            "rejected_at",
            "rejection_reason",
            "revision_reason",
            "created_at",
            "updated_at",
        ]


class QuotationSerializer(serializers.ModelSerializer):
    current_version_detail = QuotationVersionSerializer(
        source="current_version", read_only=True
    )
    accepted_version_detail = QuotationVersionSerializer(
        source="accepted_version", read_only=True
    )
    all_versions = QuotationVersionSerializer(
        source="versions", many=True, read_only=True
    )

    class Meta:
        model = Quotation
        fields = [
            "id",
            "quotation_number",
            "lead",
            "customer",
            "status",
            "current_version",
            "current_version_detail",
            "accepted_version",
            "accepted_version_detail",
            "all_versions",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "quotation_number",
            "lead",
            "customer",
            "status",
            "current_version",
            "current_version_detail",
            "accepted_version",
            "accepted_version_detail",
            "all_versions",
            "created_by",
            "created_at",
            "updated_at",
        ]


class QuotationIntegrationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationIntegrationEvent
        fields = [
            "id",
            "event_type",
            "lead",
            "customer",
            "quotation",
            "quotation_version_number",
            "payload",
            "status",
            "created_at",
        ]
        read_only_fields = fields
