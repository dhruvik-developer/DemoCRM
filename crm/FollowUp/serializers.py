from rest_framework import serializers
from .models import (
    Followup,
    FollowUpStatus,
    FollowUpTypes,
)
from django.utils import timezone


class FollowUpStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpStatus
        fields = "__all__"

    def validate_status_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Follow-up status cannot be empty.")

        return value


class FollowUpTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpTypes
        fields = "__all__"

    def validate_type_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Follow-up type cannot be empty.")

        return value


class FollowupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Followup
        fields = "__all__"
        read_only_fields = (
            "followup_id",
            "created_by",
            "created_at",
            "updated_at",
        )

    def validate_followup_date(self, value):
        if value:
            if self.instance and self.instance.followup_date == value:
                return value
            if value < timezone.now():
                raise serializers.ValidationError(
                    "Follow-up date cannot be in the past."
                )

        return value

    def validate_decription(self, value):
        if value:
            value = value.strip()

        return value


class FollowUpStatusUpdateSerializer(serializers.Serializer):
    status_id = serializers.IntegerField(required=True)

    def validate_status_id(self, value):
        if not FollowUpStatus.objects.filter(
            followup_status_id=value, is_active=True
        ).exists():
            raise serializers.ValidationError("Invalid or inactive follow-up status.")

        return value
