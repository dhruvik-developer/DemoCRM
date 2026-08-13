from django.contrib.auth import get_user_model

from rest_framework import serializers

from Task.models import Task
from .models import Followup, FollowUpNote, FollowUpStatus, FollowUpTypes, ActivityAction, ActivityLog, ActivityType, Notification, NotificationTemplate, NotificationType
from .notification_utils import build_context, render_template

from django.utils import timezone

User = get_user_model()
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
            "created_by",
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


class NotificationSendSerializer(serializers.Serializer):
    """Used by the preview and send endpoints.

    - recipients : list of CustomUser UUIDs (one or many)
    - template_id: chosen NotificationTemplate
    - message    : optional customized message (Admin/Manager only)
    - task_id / followup_id: optional context for placeholders
    - scheduled_at: optional future date to defer sending
    """

    recipients = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
    )
    template_id = serializers.IntegerField(write_only=True)
    notification_type_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
    )
    message = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
    )
    task_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
    )
    followup_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
    )
    scheduled_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        write_only=True,
    )

    def validate_recipients(self, value):
        recipients = list(
            User.objects.filter(user_id__in=value)
        )

        if len(recipients) != len(set(value)):
            found = {str(user.user_id) for user in recipients}
            missing = [str(uid) for uid in value if str(uid) not in found]
            raise serializers.ValidationError(
                f"Recipient(s) not found: {missing}"
            )

        return recipients

    def validate_template_id(self, value):
        template = NotificationTemplate.objects.filter(
            template_id=value,
            is_active=True,
        ).first()

        if template is None:
            raise serializers.ValidationError(
                "Template not found or inactive."
            )

        return template

    def validate_task_id(self, value):
        if value is None:
            return value

        if not Task.objects.filter(task_id=value).exists():
            raise serializers.ValidationError(
                "Task not found."
            )

        return value

    def validate_followup_id(self, value):
        if value is None:
            return value

        if not Followup.objects.filter(followup_id=value).exists():
            raise serializers.ValidationError(
                "Follow-up not found."
            )

        return value

    def validate_scheduled_at(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError(
                "scheduled_at must be in the future."
            )

        return value

    def context_data(self):
        """Build the placeholder context from validated data."""
        task = None
        followup = None

        if self.validated_data.get("task_id"):
            task = Task.objects.get(
                task_id=self.validated_data["task_id"]
            )

        if self.validated_data.get("followup_id"):
            followup = Followup.objects.get(
                followup_id=self.validated_data["followup_id"]
            )

        recipient = self.validated_data["recipients"][0]

        return build_context(recipient, task=task, followup=followup)

    def rendered(self):
        """Return (subject, body) for the template + context.

        If a customized message was provided it is returned as the body.
        """
        template = self.validated_data["template_id"]
        subject, body = render_template(
            template,
            self.context_data(),
        )

        customized = self.validated_data.get("message")
        if customized:
            body = customized

        return subject, body

    def notification_type(self):
        """Resolve the type for created notifications."""
        type_id = self.validated_data.get("notification_type_id")
        if type_id:
            notification_type = NotificationType.objects.filter(
                notification_type_id=type_id,
                is_active=True,
            ).first()
            if notification_type:
                return notification_type

        template = self.validated_data["template_id"]
        if template.notification_type_id:
            return template.notification_type_id

        notification_type, _ = NotificationType.objects.get_or_create(
            type_name="System"
        )
        return notification_type


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = (
            "notification_id",
            "created_at",
            "sent_at",
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
        is_read = attrs.get("is_read", getattr(self.instance, "is_read", False))
        read_at = attrs.get("read_at", getattr(self.instance, "read_at", None))

        if not is_read and read_at is not None:
            raise serializers.ValidationError({
                "read_at": "read_at must be empty when notification is unread."
            })

        if is_read and read_at is None:
            raise serializers.ValidationError({
                "read_at": "read_at is required when notification is read."
            })
        return attrs