from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Notification,
    NotificationTemplate,
    NotificationChannel,
    NotificationEventType,
)

User = get_user_model()


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "name",
            "event_type",
            "message",
            "channel",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_channel(self, value):
        if value not in NotificationChannel.values:
            raise serializers.ValidationError(
                f"Invalid channel. Must be one of {NotificationChannel.values}"
            )
        return value


class NotificationSerializer(serializers.ModelSerializer):
    recipient_email = serializers.EmailField(source="recipient.email", read_only=True)
    recipient_name = serializers.CharField(source="recipient.username", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient",
            "recipient_email",
            "recipient_name",
            "template",
            "event_type",
            "message",
            "channel",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "recipient",
            "template",
            "event_type",
            "message",
            "channel",
            "created_at",
        ]


class ManualNotificationSerializer(serializers.Serializer):
    recipient_id = serializers.UUIDField(required=False, allow_null=True)
    recipient_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_null=True
    )
    template_id = serializers.IntegerField(required=False, allow_null=True)
    event_type = serializers.CharField(
        required=False, default=NotificationEventType.MANUAL
    )
    custom_message = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    channel = serializers.ChoiceField(
        choices=NotificationChannel.choices, required=False, allow_null=True
    )

    def validate(self, attrs):
        recipient_id = attrs.get("recipient_id")
        recipient_ids = attrs.get("recipient_ids")

        if not recipient_id and not recipient_ids:
            raise serializers.ValidationError(
                "Either recipient_id or recipient_ids must be provided."
            )

        users = []
        if recipient_id:
            try:
                user = User.objects.get(pk=recipient_id)
                users.append(user)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {"recipient_id": f"User with ID '{recipient_id}' not found."}
                )

        if recipient_ids:
            for uid in recipient_ids:
                try:
                    user = User.objects.get(pk=uid)
                    if user not in users:
                        users.append(user)
                except User.DoesNotExist:
                    raise serializers.ValidationError(
                        {"recipient_ids": f"User with ID '{uid}' not found."}
                    )

        attrs["recipients"] = users

        template_id = attrs.get("template_id")
        if template_id:
            if not NotificationTemplate.objects.filter(pk=template_id).exists():
                raise serializers.ValidationError(
                    {
                        "template_id": f"NotificationTemplate with ID {template_id} does not exist."
                    }
                )

        return attrs
