import json

from rest_framework import serializers
from django.utils import timezone
from .models import (
    TaskPriority,
    TaskCategory,
    TaskStatus,
    Task,
    MeetingParticipant,
    MeetingStatus,
    Meeting,
    MeetingType,
    ReminderType,
    ReminderStatus,
    Reminder,
)
from accounts.models import CustomUser

# ============================================================
# TASK
# ============================================================


class TaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatus
        fields = "__all__"

    def validate_status_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Status name cannot be empty.")

        if len(value) < 2:
            raise serializers.ValidationError(
                "Status name must contain at least 2 characters."
            )

        return value


class TaskPrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskPriority
        fields = "__all__"

    def validate_priority_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Priority name cannot be empty.")

        return value


class TaskCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskCategory
        fields = "__all__"

    def validate_category_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Category name cannot be empty.")

        return value


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = (
            "task_id",
            "created_by",
            "created_at",
            "updated_at",
        )

    def validate_task_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Task title is required.")

        if len(value) < 3:
            raise serializers.ValidationError(
                "Task title must contain at least 3 characters."
            )

        if len(value) > 200:
            raise serializers.ValidationError(
                "Task title cannot exceed 200 characters."
            )

        return value

    def validate_description(self, value):
        if value:
            value = value.strip()

        return value

    def validate_due_date(self, value):
        if value:
            if self.instance and self.instance.due_date == value:
                return value
            if value < timezone.now():
                raise serializers.ValidationError("Due date cannot be in the past.")

        return value

    def validate(self, attrs):
        lead = attrs.get("lead", getattr(self.instance, "lead", None))

        if not lead:
            raise serializers.ValidationError(
                {"lead": "Lead is required to create a task."}
            )

        return attrs


# ============================================================
# MEETING
# ============================================================


class MeetingStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingStatus
        fields = "__all__"

    def validate_status_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Meeting status cannot be empty.")

        return value


class MeetingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingType
        fields = "__all__"

    def validate_type_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Meeting type cannot be empty.")

        return value


class MeetingSerializer(serializers.ModelSerializer):
    manager = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role__rolename__iexact="manager", is_active=True),
        required=True,
    )
    manager_name = serializers.SerializerMethodField()
    requested_by_name = serializers.SerializerMethodField()
    task_title = serializers.CharField(source="task_id.task_title", read_only=True)
    participant_details = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = "__all__"
        read_only_fields = (
            "meeting_id",
            "created_by",
            "created_at",
            "updated_at",
            "approval_status",
            "approved_by",
            "approved_at",
            "rejection_reason",
            "reminder_sent_at",
            "meeting_link",
        )

    def validate_meeting_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Meeting title is required.")

        if len(value) < 3:
            raise serializers.ValidationError(
                "Meeting title must contain at least 3 characters."
            )

        return value

    def validate_custom_fields(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Custom fields must be an object.")
        definitions = value.get("definitions", [])
        values = value.get("values", {})
        if not isinstance(definitions, list) or not isinstance(values, dict):
            raise serializers.ValidationError("Invalid custom-field structure.")
        if len(definitions) > 25:
            raise serializers.ValidationError("A task can have at most 25 custom fields.")
        if len(json.dumps(value, default=str).encode("utf-8")) > 20_000:
            raise serializers.ValidationError("Custom-field data is too large.")
        return value

    def get_manager_name(self, meeting):
        user = meeting.manager
        return user.get_full_name() or user.username or user.email

    def get_requested_by_name(self, meeting):
        user = meeting.created_by
        return user.get_full_name() or user.username or user.email

    def get_participant_details(self, meeting):
        participants = meeting.participants.select_related("user_id").all()
        return [
            {
                "participant_id": participant.participant_id,
                "user_id": participant.user_id_id,
                "name": participant.user_id.get_full_name() or participant.user_id.username,
                "email": participant.user_id.email,
                "role": participant.participant_role,
                "is_required": participant.is_required,
            }
            for participant in participants
        ]

    def validate_meeting_date(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError("Meeting date cannot be in the past.")
        return value

    def validate_start_time(self, value):
        return value

    def validate_end_time(self, value):
        return value

    def validate(self, attrs):
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))

        if start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError(
                    {"end_time": "End time must be after start time."}
                )
        meeting_date = attrs.get(
            "meeting_date",
            getattr(
                self.instance,
                "meeting_date",
                None,
            ),
        )
        if meeting_date and not self.instance and meeting_date < timezone.localdate():
            raise serializers.ValidationError(
                {"meeting_date": "Meeting date cannot be in the past."}
            )
        return attrs


class MeetingParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingParticipant
        fields = "__all__"
        read_only_fields = ("participant_id",)

    def validate_participant_role(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Participant role is required.")

        return value


# ============================================================
# REMINDER
# ============================================================


class ReminderTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderType
        fields = "__all__"

    def validate_type_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Reminder type cannot be empty.")

        return value


class ReminderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderStatus
        fields = "__all__"

    def validate_status_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Reminder status cannot be empty.")

        return value


class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = "__all__"
        read_only_fields = (
            "reminder_id",
            "created_by",
            "created_at",
            "updated_at",
        )

    def validate_message(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Reminder message is required.")

        return value

    def validate_reminder_datetime(self, value):
        if self.instance and self.instance.reminder_datetime == value:
            return value
        if value < timezone.now():
            raise serializers.ValidationError(
                "Reminder date and time cannot be in the past."
            )

        return value
