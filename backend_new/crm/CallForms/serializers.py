import re
from rest_framework import serializers
from .models import (
    AdhocFieldProposal,
    CallAttempt,
    CallTemplate,
    FieldType,
    FormSubmission,
    IndexedSubmissionValue,
    OutcomeChoice,
    PipelineStageActivity,
    TaskTriggerRule,
    TemplateField,
    TemplateVersion,
)


class TemplateFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateField
        fields = [
            "id",
            "template_version",
            "field_key",
            "label",
            "field_type",
            "is_required",
            "display_order",
            "help_text",
            "options",
            "validation_rules",
        ]
        read_only_fields = ["id"]

    def validate_field_key(self, value):
        if not re.match(r"^[a-z0-9_]+$", value.lower()):
            raise serializers.ValidationError(
                "field_key must contain only lowercase alphanumeric characters and underscores."
            )
        return value.lower()

    def validate(self, attrs):
        field_type = attrs.get(
            "field_type", getattr(self.instance, "field_type", FieldType.TEXT)
        )
        options = attrs.get("options", getattr(self.instance, "options", []))

        if field_type == FieldType.SELECT and not options:
            raise serializers.ValidationError(
                {"options": "Select field type requires a non-empty list of options."}
            )

        template_version = attrs.get(
            "template_version", getattr(self.instance, "template_version", None)
        )
        if template_version and template_version.is_locked:
            raise serializers.ValidationError(
                "Cannot add or modify fields on a locked template version."
            )

        return attrs


class TemplateVersionSerializer(serializers.ModelSerializer):
    is_locked = serializers.BooleanField(read_only=True)

    class Meta:
        model = TemplateVersion
        fields = [
            "id",
            "template",
            "version_number",
            "version_label",
            "is_primary",
            "is_active",
            "is_locked",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "is_locked", "created_by", "created_at"]


class TemplateVersionDetailSerializer(TemplateVersionSerializer):
    fields = TemplateFieldSerializer(many=True, read_only=True)

    class Meta(TemplateVersionSerializer.Meta):
        fields = TemplateVersionSerializer.Meta.fields + ["fields"]


class CallTemplateSerializer(serializers.ModelSerializer):
    primary_version = serializers.SerializerMethodField()
    version_count = serializers.SerializerMethodField()

    class Meta:
        model = CallTemplate
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
            "primary_version",
            "version_count",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_primary_version(self, obj):
        primary = obj.versions.filter(is_primary=True).first()
        if primary:
            return TemplateVersionSerializer(primary).data
        return None

    def get_version_count(self, obj):
        return obj.versions.count()


class CallTemplateDetailSerializer(CallTemplateSerializer):
    versions = TemplateVersionSerializer(many=True, read_only=True)

    class Meta(CallTemplateSerializer.Meta):
        fields = CallTemplateSerializer.Meta.fields + ["versions"]


class CreateTemplateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    is_active = serializers.BooleanField(default=True)
    initial_fields = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )

    def validate_name(self, value):
        if CallTemplate.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                "A call template with this name already exists."
            )
        return value


class CloneVersionSerializer(serializers.Serializer):
    version_label = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    set_primary = serializers.BooleanField(default=True)


class FieldOrderEntrySerializer(serializers.Serializer):
    field_id = serializers.UUIDField()
    display_order = serializers.IntegerField(min_value=1)


class ReorderFieldsSerializer(serializers.Serializer):
    template_version_id = serializers.UUIDField()
    orders = serializers.ListField(child=FieldOrderEntrySerializer())


class PipelineStageActivitySerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    call_template_name = serializers.CharField(
        source="call_template.name", read_only=True
    )

    class Meta:
        model = PipelineStageActivity
        fields = [
            "id",
            "stage",
            "stage_name",
            "name",
            "description",
            "activity_type",
            "call_template",
            "call_template_name",
            "is_primary",
            "display_order",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class PipelineStageActivityDetailSerializer(PipelineStageActivitySerializer):
    call_template_detail = CallTemplateSerializer(
        source="call_template", read_only=True
    )

    class Meta(PipelineStageActivitySerializer.Meta):
        fields = PipelineStageActivitySerializer.Meta.fields + ["call_template_detail"]


class CallAttemptSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    agent_name = serializers.CharField(source="agent.username", read_only=True)
    outcome_display = serializers.CharField(
        source="get_outcome_display", read_only=True
    )

    class Meta:
        model = CallAttempt
        fields = [
            "id",
            "lead",
            "lead_name",
            "stage",
            "activity",
            "template_version",
            "attempt_number",
            "agent",
            "agent_name",
            "outcome",
            "outcome_display",
            "notes",
            "start_time",
            "end_time",
            "is_form_submitted",
            "suggest_mark_lost",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "attempt_number",
            "agent",
            "is_form_submitted",
            "created_at",
        ]


class LogCallAttemptSerializer(serializers.Serializer):
    lead_id = serializers.UUIDField()
    stage_id = serializers.UUIDField(required=False, allow_null=True)
    activity_id = serializers.UUIDField(required=False, allow_null=True)
    template_version_id = serializers.UUIDField(required=False, allow_null=True)
    outcome = serializers.ChoiceField(
        choices=OutcomeChoice.choices, default=OutcomeChoice.NO_ANSWER
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    start_time = serializers.DateTimeField(required=False, allow_null=True)
    end_time = serializers.DateTimeField(required=False, allow_null=True)


class FormSubmissionSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    submitted_by_name = serializers.CharField(
        source="submitted_by.username", read_only=True
    )
    template_name = serializers.CharField(
        source="template_version.template.name", read_only=True
    )
    version_label = serializers.CharField(
        source="template_version.version_label", read_only=True
    )
    adhoc_fields = serializers.SerializerMethodField()

    class Meta:
        model = FormSubmission
        fields = [
            "id",
            "lead",
            "lead_name",
            "call_attempt",
            "template_version",
            "template_name",
            "version_label",
            "quotation",
            "submitted_by",
            "submitted_by_name",
            "data",
            "adhoc_fields",
            "notes",
            "created_at",
        ]
        # Historical integrity: a submission's lead, schema version, payload,
        # and linked call attempt/quotation are immutable after creation.
        # Only ``notes`` may be edited after the fact.
        read_only_fields = [
            "id",
            "lead",
            "call_attempt",
            "template_version",
            "data",
            "quotation",
            "submitted_by",
            "created_at",
        ]

    def get_adhoc_fields(self, obj):
        from .services import get_submission_adhoc_fields

        return get_submission_adhoc_fields(obj)


class SubmitCallFormSerializer(serializers.Serializer):
    lead_id = serializers.UUIDField()
    template_version_id = serializers.UUIDField()
    call_attempt_id = serializers.UUIDField(required=False, allow_null=True)
    # Optional link for stage-specific forms such as "Quotation Discussion".
    quotation_id = serializers.UUIDField(required=False, allow_null=True)
    data = serializers.DictField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class TaskTriggerRuleSerializer(serializers.ModelSerializer):
    version_label = serializers.CharField(
        source="template_version.version_label", read_only=True
    )

    class Meta:
        model = TaskTriggerRule
        fields = [
            "id",
            "template_version",
            "version_label",
            "name",
            "trigger_condition",
            "condition_field_key",
            "condition_value",
            "task_title_template",
            "task_category",
            "task_priority",
            "due_days_offset",
            "assignee_rule",
            "specific_assignee",
            "create_reminder",
            "reminder_minutes_before",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdhocFieldProposalSerializer(serializers.ModelSerializer):
    proposed_by_username = serializers.CharField(
        source="proposed_by.username", read_only=True
    )
    reviewed_by_username = serializers.CharField(
        source="reviewed_by.username", read_only=True
    )

    class Meta:
        model = AdhocFieldProposal
        fields = [
            "id",
            "template_version",
            "field_key",
            "label",
            "field_type",
            "help_text",
            "options",
            "status",
            "proposed_by",
            "proposed_by_username",
            "reviewed_by",
            "reviewed_by_username",
            "reviewed_at",
            "rejection_reason",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "proposed_by",
            "reviewed_by",
            "reviewed_at",
            "created_at",
        ]

    def validate_field_key(self, value):
        if not re.match(r"^[a-z0-9_]+$", value.lower()):
            raise serializers.ValidationError(
                "field_key must contain only lowercase alphanumeric characters and underscores."
            )
        return value.lower()


class ReviewAdhocFieldProposalSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["APPROVED", "REJECTED"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class IndexedSubmissionValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndexedSubmissionValue
        fields = [
            "id",
            "submission",
            "field_key",
            "value_text",
            "value_number",
            "value_date",
            "value_boolean",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
