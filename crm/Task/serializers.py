from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from .models import TaskPriority, TaskCategory, TaskStatus, Task, MeetingParticipant, MeetingStatus, Meeting, MeetingType, ReminderType, ReminderStatus, Reminder

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
            raise serializers.ValidationError(
                "Status name cannot be empty."
            )

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
            raise serializers.ValidationError(
                "Priority name cannot be empty."
            )

        return value


class TaskCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskCategory
        fields = "__all__"

    def validate_category_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Category name cannot be empty."
            )

        return value


class TaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = (
            "task_id",
            "created_at",
            "updated_at",
        )

    def validate_task_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Task title is required."
            )

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
                raise serializers.ValidationError(
                    "Due date cannot be in the past."
                )

        return value

    def validate(self, attrs):
        assigned_to = attrs.get("assigned_to")
        created_by = attrs.get("created_by")

        if assigned_to and created_by and assigned_to == created_by:
            # This is NOT necessarily an error in a CRM.
            # So we allow it.
            pass

        return attrs

# ============================================================
# MEETING STATUS
# ============================================================

class MeetingStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = MeetingStatus
        fields = "__all__"

    def validate_status_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Meeting status name cannot be empty."
            )

        if len(value) < 2:
            raise serializers.ValidationError(
                "Meeting status name must contain at least 2 characters."
            )

        return value


# ============================================================
# MEETING TYPE
# ============================================================

class MeetingTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = MeetingType
        fields = "__all__"

    def validate_type_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Meeting type name cannot be empty."
            )

        if len(value) < 2:
            raise serializers.ValidationError(
                "Meeting type name must contain at least 2 characters."
            )

        return value


# ============================================================
# MEETING
# ============================================================

class MeetingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Meeting
        fields = "__all__"

        read_only_fields = (
            "meeting_id",
            "updated_at",
            "created_by", 
        )

    def validate_meeting_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Meeting title is required."
            )

        if len(value) < 3:
            raise serializers.ValidationError(
                "Meeting title must contain at least 3 characters."
            )

        if len(value) > 100:
            raise serializers.ValidationError(
                "Meeting title cannot exceed 100 characters."
            )

        return value

    def validate_location(self, value):
        if value:
            value = value.strip()

        return value

    def validate_description(self, value):
        if value:
            value = value.strip()

        return value

    def validate_meeting_date(self, value):

        today = timezone.localdate()

        if value < today:
            raise serializers.ValidationError(
                "Meeting date cannot be in the past."
            )

        return value

    def validate(self, attrs):

        meeting_date = attrs.get("meeting_date")
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")

        # For update, use existing values if they are not provided.
        if self.instance:
            meeting_date = (
                meeting_date
                if meeting_date is not None
                else self.instance.meeting_date
            )

            start_time = (
                start_time
                if start_time is not None
                else self.instance.start_time
            )

            end_time = (
                end_time
                if end_time is not None
                else self.instance.end_time
            )

        if start_time and end_time:

            if end_time <= start_time:
                raise serializers.ValidationError({
                    "end_time": "End time must be after start time."
                })

        # Prevent scheduling a meeting in the past.
        if meeting_date and start_time:

            meeting_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    meeting_date,
                    start_time
                )
            )

            if meeting_datetime < timezone.now():

                # During update, allow unchanged existing meeting time.
                if not self.instance or (
                    self.instance.meeting_date != meeting_date
                    or self.instance.start_time != start_time
                ):
                    raise serializers.ValidationError({
                        "meeting_date": (
                            "Meeting date and start time "
                            "cannot be in the past."
                        )
                    })

        return attrs


# ============================================================
# MEETING PARTICIPANT
# ============================================================

class MeetingParticipantSerializer(serializers.ModelSerializer):

    class Meta:
        model = MeetingParticipant
        fields = "__all__"

        read_only_fields = (
            "participant_id",
        )

    def validate_participant_role(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Participant role is required."
            )

        if len(value) < 2:
            raise serializers.ValidationError(
                "Participant role must contain at least 2 characters."
            )

        return value

    def validate(self, attrs):

        meeting = attrs.get("meeting_id")
        user = attrs.get("user_id")

        if meeting and user:

            # Prevent duplicate participant in same meeting.
            queryset = MeetingParticipant.objects.filter(
                meeting_id=meeting,
                user_id=user
            )

            if self.instance:
                queryset = queryset.exclude(
                    participant_id=self.instance.participant_id
                )

            if queryset.exists():
                raise serializers.ValidationError({
                    "user_id": (
                        "This user is already a participant "
                        "in this meeting."
                    )
                })

        return attrs


# ============================================================
# REMINDER TYPE
# ============================================================

class ReminderTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReminderType
        fields = "__all__"

    def validate_type_name(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Reminder type name cannot be empty."
            )

        if len(value) < 2:
            raise serializers.ValidationError(
                "Reminder type name must contain at least 2 characters."
            )

        return value


# ============================================================
# REMINDER STATUS
# ============================================================

class ReminderStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReminderStatus
        fields = "__all__"

    def validate_status_name(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Reminder status name cannot be empty."
            )

        if len(value) < 2:
            raise serializers.ValidationError(
                "Reminder status name must contain at least 2 characters."
            )

        return value


# ============================================================
# REMINDER
# ============================================================

class ReminderSerializer(serializers.ModelSerializer):

    class Meta:
        model = Reminder
        fields = "__all__"

        read_only_fields = (
            "reminder_id",
            "created_at",
            "updated_at",
        )

    def validate_message(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Reminder message is required."
            )

        return value

    def validate_reminder_datetime(self, value):

        if value < timezone.now():

            if not self.instance or (
                self.instance.reminder_datetime != value
            ):
                raise serializers.ValidationError(
                    "Reminder date and time cannot be in the past."
                )

        return value

    def validate(self, attrs):

        task = attrs.get("task_id")
        meeting = attrs.get("meeting_id")

        # Reminder should belong to either a task or a meeting.
        if not task and not meeting:
            raise serializers.ValidationError(
                "Reminder must be linked to a task or a meeting."
            )

        # If meeting is provided, task can automatically be
        # understood from meeting.task_id, but we don't force it here.

        return attrs