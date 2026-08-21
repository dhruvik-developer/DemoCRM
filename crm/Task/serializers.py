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
            "created_by",
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
        customer = attrs.get("customer", getattr(self.instance, "customer", None))

        if not lead and not customer:
            raise serializers.ValidationError(
                {"lead": "At least a Lead or Customer is required to create a task."}
            )

        if customer and not lead:
            attrs["lead"] = customer.lead

        if customer and lead:
            if customer.lead_id != lead.pk:
                raise serializers.ValidationError(
                    {"customer": "Customer must belong to the assigned Lead."}
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
        queryset=CustomUser.objects.all(),
        required=True
    )

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
        if (
            meeting_date
            and not self.instance
            and meeting_date < timezone.localdate()
        ):
            raise serializers.ValidationError({
                "meeting_date":
                "Meeting date cannot be in the past."
            })
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

    def validate(self, attrs):
        task = attrs.get("task_id", getattr(self.instance, "task_id", None))
        meeting = attrs.get("meeting_id", getattr(self.instance, "meeting_id", None))

        if not task and not meeting:
            raise serializers.ValidationError(
                {"task_id": "At least a Task or Meeting is required for a reminder."}
            )

        if task and meeting:
            if meeting.task_id_id != task.pk:
                raise serializers.ValidationError(
                    {"meeting_id": "Meeting must belong to the specified Task."}
                )

        return attrs
