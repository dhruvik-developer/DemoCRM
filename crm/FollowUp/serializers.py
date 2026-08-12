from rest_framework import serializers
from .models import Followup,FollowUpNote,FollowUpStatus,FollowUpTypes,ActivityAction,ActivityLog,ActivityType,Notification,NotificationTemplate,NotificationType
from django.utils import timezone
class FollowUpStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = FollowUpStatus
        fields = "__all__"

    def validate_status_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Follow-up status cannot be empty."
            )

        return value


class FollowUpTypesSerializer(serializers.ModelSerializer):

    class Meta:
        model = FollowUpTypes
        fields = "__all__"

    def validate_type_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Follow-up type cannot be empty."
            )

        return value


class FollowupSerializer(serializers.ModelSerializer):

    class Meta:
        model = Followup
        fields = "__all__"
        read_only_fields = (
            "followup_id",
            "created_at",
            "updated_at",
        )

    def validate_followup_date(self, value):
        if value < timezone.now():
            raise serializers.ValidationError(
                "Follow-up date cannot be in the past."
            )

        return value

    def validate_decription(self, value):
        if value:
            value = value.strip()

        return value


class FollowUpNoteSerializer(serializers.ModelSerializer):

    class Meta:
        model = FollowUpNote
        fields = "__all__"
        read_only_fields = (
            "note_id",
            "created_at",
        )

    def validate_note(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Note cannot be empty."
            )

        if len(value) < 2:
            raise serializers.ValidationError(
                "Note must contain at least 2 characters."
            )

        return value

# ============================================================
# ACTIVITY LOG
# ============================================================

class ActivityTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActivityType
        fields = "__all__"


class ActivityActionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActivityAction
        fields = "__all__"


class ActivityLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActivityLog
        fields = "__all__"
        read_only_fields = (
            "activity_id",
            "created_at",
        )

    def validate_description(self, value):
        if value:
            value = value.strip()

        return value

    def validate_reference_id(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Reference ID must be greater than 0."
            )

        return value

# ============================================================
# NOTIFICATION
# ============================================================

class NotificationTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = NotificationType
        fields = "__all__"

    def validate_type_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Notification type cannot be empty."
            )

        return value


class NotificationTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = NotificationTemplate
        fields = "__all__"
        read_only_fields = (
            "template_id",
        )

    def validate_subject(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Subject is required."
            )

        return value

    def validate_body(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Template body is required."
            )

        return value


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = (
            "notification_id",
            "created_at",
        )

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Notification title is required."
            )

        return value

    def validate_message(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Notification message is required."
            )

        return value

    def validate(self, attrs):
        is_read = attrs.get("is_read", False)
        read_at = attrs.get("read_at")

        if not is_read and read_at is not None:
            raise serializers.ValidationError({
                "read_at": "read_at must be empty when notification is unread."
            })

        if is_read and read_at is None:
            raise serializers.ValidationError({
                "read_at": "read_at is required when notification is read."
            })
        return attrs