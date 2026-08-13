from rest_framework import serializers

from .models import (
    Activity,
    AuditLog,
    Customer,
    Lead,
    LeadSource,
    Pipeline,
    PipelineStage,
)


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
                {
                    "pipeline": "Cannot use an inactive pipeline."
                }
            )

        display_order = attrs.get("display_order")

        if display_order is not None and display_order < 1:
            raise serializers.ValidationError(
                {
                    "display_order": "Display order must be at least 1."
                }
            )

        return attrs


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "company_name",
            "source",
            "assigned_to",
            "pipeline",
            "current_stage",
            "status",
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
                {
                    "source": "Cannot use an inactive lead source."
                }
            )

        if pipeline and not pipeline.is_active:
            raise serializers.ValidationError(
                {
                    "pipeline": "Cannot use an inactive pipeline."
                }
            )

        target_pipeline_id = (
            pipeline.id
            if pipeline
            else (self.instance.pipeline_id if self.instance else None)
        )

        if current_stage:
            if not current_stage.is_active:
                raise serializers.ValidationError(
                    {
                        "current_stage": "Cannot use an inactive stage."
                    }
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
                {
                    "assigned_to": (
                        "An inactive employee cannot be assigned a Lead."
                    )
                }
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
            self.instance is None
            or self.instance.status != Lead.Status.LOST
        ):
            raise serializers.ValidationError(
                {
                    "lost_reason": "Lost reason can only be set on a lost Lead."
                }
            )

        return attrs


class CustomerSerializer(serializers.ModelSerializer):
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
                        "Follow-up date is required when "
                        "follow-up is required."
                    )
                }
            )

        if not follow_up_required and follow_up_date:
            raise serializers.ValidationError(
                {
                    "follow_up_date": (
                        "Follow-up date cannot be set when "
                        "follow-up is not required."
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