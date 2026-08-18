import logging

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import TaskHasPermission

from .models import (
    Task,
    TaskStatus,
    Meeting,
    MeetingStatus,
    MeetingParticipant,
    Reminder,
    ReminderStatus,
)

from .serializers import (
    TaskSerializer,
    MeetingSerializer,
    MeetingParticipantSerializer,
    ReminderSerializer,
)

from Notification.notification_utils import trigger_notification_event
from Notification.models import NotificationEventType
from Notification.notification_utils import create_notification

User = get_user_model()


# ==========================================================
# TASK
# ==========================================================

class TaskListCreateView(APIView):
    """
    GET  /api/tasks/
        List all active tasks

    POST /api/tasks/
        Create a task
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "GET": "view_task",
        "POST": "add_task",
    }

    def get(self, request):

        tasks = (
            Task.objects
            .filter(is_active=True)
            .select_related(
                "assigned_to",
                "created_by",
                "lead",
                "customer",
                "status",
                "priority",
                "category",
            )
            .order_by("-created_at")
        )

        serializer = TaskSerializer(
            tasks,
            many=True,
            context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def post(self, request):

        serializer = TaskSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():

            # We do NOT trust created_by from frontend.
            # The logged-in user becomes the creator.
            task = serializer.save(
                created_by=request.user
            )

            # Auto-notify the assignee when a task is created.
            if task.assigned_to and task.assigned_to != request.user:
                trigger_notification_event(
                    event_type=NotificationEventType.TASK_ASSIGNED,
                    recipient=task.assigned_to,
                    context={
                        "user_name": task.assigned_to.get_full_name() or task.assigned_to.username,
                        "manager_name": request.user.get_full_name() or request.user.username,
                        "task_title": task.task_title,
                        "task_id": task.task_id,
                        "due_date": str(task.due_date) if task.due_date else "",
                    },
                )
            logger.info("Task created: %s (ID: %s) by user %s", task.task_title, task.task_id, request.user.user_id)

            return Response(
                TaskSerializer(
                    task,
                    context={"request": request}
                ).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class TaskDetailView(APIView):
    """
    GET    /api/tasks/<task_id>/
        Task detail

    PATCH  /api/tasks/<task_id>/
        Update task

    DELETE /api/tasks/<task_id>/
        Soft delete task
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "GET": "view_task",
        "PATCH": "change_task",
        "DELETE": "delete_task",
    }

    def get_task(self, task_id):

        return get_object_or_404(
            Task.objects.select_related(
                "assigned_to",
                "created_by",
                "lead",
                "customer",
                "status",
                "priority",
                "category",
            ),
            task_id=task_id,
            is_active=True
        )

    # ------------------------------------------------------
    # TASK DETAIL
    # ------------------------------------------------------

    def get(self, request, task_id):

        task = self.get_task(task_id)

        serializer = TaskSerializer(
            task,
            context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    # ------------------------------------------------------
    # UPDATE TASK
    # ------------------------------------------------------

    def patch(self, request, task_id):

        task = self.get_task(task_id)

        serializer = TaskSerializer(
            task,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():

            task = serializer.save()

            if task.assigned_to:
                trigger_notification_event(
                    event_type=NotificationEventType.TASK_UPDATED,
                    recipient=task.assigned_to,
                    context={
                        "user_name": task.assigned_to.get_full_name() or task.assigned_to.username,
                        "task_title": task.task_title,
                        "task_id": task.task_id,
                    },
                )

            return Response(
                TaskSerializer(
                    task,
                    context={"request": request}
                ).data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # ------------------------------------------------------
    # DELETE TASK
    # ------------------------------------------------------

    def delete(self, request, task_id):

        task = self.get_task(task_id)

        # Soft delete because Task has is_active.
        task.is_active = False
        task.save(update_fields=["is_active"])

        # Notify the assignee about task deletion.
        if task.assigned_to and task.assigned_to != request.user:
            trigger_notification_event(
                event_type=NotificationEventType.TASK_DELETED,
                recipient=task.assigned_to,
                context={
                    "user_name": task.assigned_to.get_full_name() or task.assigned_to.username,
                    "manager_name": request.user.get_full_name() or request.user.username,
                    "task_title": task.task_title,
                    "task_id": task.task_id,
                },
            )

        return Response(
            {
                "message": "Task deleted successfully.",
                "task_id": task.task_id
            },
            status=status.HTTP_200_OK
        )


# ==========================================================
# ASSIGN TASK
# ==========================================================

class TaskAssignView(APIView):
    """
    POST /api/tasks/<task_id>/assign/

    Assign or reassign a task.
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "POST": "assign_task",
    }

    def post(self, request, task_id):

        task = get_object_or_404(
            Task,
            task_id=task_id,
            is_active=True
        )

        assigned_to_id = request.data.get("assigned_to")

        if not assigned_to_id:

            return Response(
                {
                    "assigned_to": "This field is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        new_user = get_object_or_404(
            User,
            pk=assigned_to_id
        )

        old_user = task.assigned_to

        task.assigned_to = new_user
        task.save(
            update_fields=[
                "assigned_to",
                "updated_at"
            ]
        )

        # Auto-notify the new assignee on (re)assignment.
        if old_user is None or old_user.user_id != new_user.user_id:
            event_name = NotificationEventType.TASK_REASSIGNED if old_user else NotificationEventType.TASK_ASSIGNED
            trigger_notification_event(
                event_type=event_name,
                recipient=new_user,
                context={
                    "user_name": new_user.get_full_name() or new_user.username,
                    "manager_name": request.user.get_full_name() or request.user.username,
                    "task_title": task.task_title,
                    "task_id": task.task_id,
                    "due_date": str(task.due_date) if task.due_date else "",
                },
            )

        return Response(
            {
                "message": "Task assigned successfully.",
                "task_id": task.task_id,
                "previous_assigned_to": (
                    old_user.pk if old_user else None
                ),
                "assigned_to": new_user.pk
            },
            status=status.HTTP_200_OK
        )


# ==========================================================
# CHANGE TASK STATUS
# ==========================================================

class TaskStatusUpdateView(APIView):
    """
    PATCH /api/tasks/<task_id>/status/

    Change task status.
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "PATCH": "change_task",
    }

    def patch(self, request, task_id):

        task = get_object_or_404(
            Task,
            task_id=task_id,
            is_active=True
        )

        status_id = request.data.get("status_id")

        if not status_id:

            return Response(
                {
                    "status_id": "This field is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        new_status = get_object_or_404(
            TaskStatus,
            status_id=status_id,
            is_active=True
        )

        old_status = task.status

        task.status = new_status
        task.save(
            update_fields=[
                "status",
                "updated_at"
            ]
        )

        if new_status.status_name.upper() in ["COMPLETED", "COMPLETE", "DONE"]:
            recipient = task.created_by if task.created_by else task.assigned_to
            if recipient:
                trigger_notification_event(
                    event_type=NotificationEventType.TASK_COMPLETED,
                    recipient=recipient,
                    context={
                        "employee_name": request.user.get_full_name() or request.user.username,
                        "user_name": recipient.get_full_name() or recipient.username,
                        "task_title": task.task_title,
                        "task_id": task.task_id,
                    },
                )
        else:
            # Notify on non-completion status changes.
            recipient = task.assigned_to if task.assigned_to else task.created_by
            if recipient and recipient != request.user:
                trigger_notification_event(
                    event_type=NotificationEventType.TASK_STATUS_CHANGED,
                    recipient=recipient,
                    context={
                        "user_name": recipient.get_full_name() or recipient.username,
                        "employee_name": request.user.get_full_name() or request.user.username,
                        "task_title": task.task_title,
                        "task_id": task.task_id,
                        "old_status": old_status.status_name,
                        "new_status": new_status.status_name,
                    },
                )

        return Response(
            {
                "message": "Task status updated successfully.",
                "task_id": task.task_id,
                "previous_status": old_status.status_name,
                "new_status": new_status.status_name
            },
            status=status.HTTP_200_OK
        )


# ==========================================================
# MEETING
# ==========================================================

class MeetingCreateView(APIView):
    """
    POST /api/meetings/

    Create a meeting.
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "POST": "add_meeting",
    }

    def post(self, request):

        serializer = MeetingSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():

            # created_by comes from authenticated user
            meeting = serializer.save(
                created_by=request.user
            )

            # Notify the task assignee about meeting creation.
            if meeting.task_id and meeting.task_id.assigned_to and meeting.task_id.assigned_to != request.user:
                trigger_notification_event(
                    event_type=NotificationEventType.MEETING_CREATED,
                    recipient=meeting.task_id.assigned_to,
                    context={
                        "user_name": meeting.task_id.assigned_to.get_full_name() or meeting.task_id.assigned_to.username,
                        "employee_name": request.user.get_full_name() or request.user.username,
                        "meeting_title": meeting.meeting_title,
                        "meeting_date": str(meeting.meeting_date),
                        "start_time": str(meeting.start_time),
                    },
                )

            return Response(
                MeetingSerializer(
                    meeting,
                    context={"request": request}
                ).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class MeetingDetailView(APIView):
    """
    GET /api/meetings/<meeting_id>/

    Get meeting details.
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "GET": "view_meeting",
    }

    def get(self, request, meeting_id):

        meeting = get_object_or_404(
            Meeting.objects.select_related(
                "task_id",
                "meeting_status_id",
                "meeting_type_id",
                "created_by",
            ),
            meeting_id=meeting_id
        )

        serializer = MeetingSerializer(
            meeting,
            context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


# ==========================================================
# RESCHEDULE MEETING
# ==========================================================

class MeetingRescheduleView(APIView):
    """
    PATCH /api/meetings/<meeting_id>/reschedule/

    Change meeting date/time.
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "PATCH": "change_meeting",
    }

    def patch(self, request, meeting_id):

        meeting = get_object_or_404(
            Meeting,
            meeting_id=meeting_id
        )

        serializer = MeetingSerializer(
            meeting,
            data={
                "meeting_date": request.data.get("meeting_date"),
                "start_time": request.data.get("start_time"),
                "end_time": request.data.get("end_time"),
            },
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():

            meeting = serializer.save()

            # Notify the task assignee about meeting reschedule.
            if meeting.task_id and meeting.task_id.assigned_to and meeting.task_id.assigned_to != request.user:
                trigger_notification_event(
                    event_type=NotificationEventType.MEETING_RESCHEDULED,
                    recipient=meeting.task_id.assigned_to,
                    context={
                        "user_name": meeting.task_id.assigned_to.get_full_name() or meeting.task_id.assigned_to.username,
                        "employee_name": request.user.get_full_name() or request.user.username,
                        "meeting_title": meeting.meeting_title,
                        "meeting_date": str(meeting.meeting_date),
                        "start_time": str(meeting.start_time),
                    },
                )

            # Also notify existing participants.
            participant_users = MeetingParticipant.objects.filter(
                meeting_id=meeting
            ).exclude(user_id=meeting.task_id.assigned_to).select_related("user_id")
            for p in participant_users:
                if p.user_id != request.user:
                    trigger_notification_event(
                        event_type=NotificationEventType.MEETING_RESCHEDULED,
                        recipient=p.user_id,
                        context={
                            "user_name": p.user_id.get_full_name() or p.user_id.username,
                            "employee_name": request.user.get_full_name() or request.user.username,
                            "meeting_title": meeting.meeting_title,
                            "meeting_date": str(meeting.meeting_date),
                            "start_time": str(meeting.start_time),
                        },
                    )

            return Response(
                {
                    "message": "Meeting rescheduled successfully.",
                    "meeting": MeetingSerializer(
                        meeting,
                        context={"request": request}
                    ).data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


# ==========================================================
# CHANGE MEETING STATUS
# ==========================================================

class MeetingStatusUpdateView(APIView):
    """
    PATCH /api/meetings/<meeting_id>/status/

    Change meeting status.
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "PATCH": "change_meeting",
    }

    def patch(self, request, meeting_id):

        meeting = get_object_or_404(
            Meeting,
            meeting_id=meeting_id
        )

        status_id = request.data.get("meeting_status_id")

        if not status_id:

            return Response(
                {
                    "meeting_status_id": "This field is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        new_status = get_object_or_404(
            MeetingStatus,
            meeting_status_id=status_id,
            is_active=True
        )

        old_status = meeting.meeting_status_id

        meeting.meeting_status_id = new_status

        meeting.save(
            update_fields=[
                "meeting_status_id",
                "updated_at"
            ]
        )

        # Notify the task assignee about meeting status change.
        if meeting.task_id and meeting.task_id.assigned_to and meeting.task_id.assigned_to != request.user:
            trigger_notification_event(
                event_type=NotificationEventType.MEETING_STATUS_CHANGED,
                recipient=meeting.task_id.assigned_to,
                context={
                    "user_name": meeting.task_id.assigned_to.get_full_name() or meeting.task_id.assigned_to.username,
                    "employee_name": request.user.get_full_name() or request.user.username,
                    "meeting_title": meeting.meeting_title,
                    "old_status": old_status.status_name,
                    "new_status": new_status.status_name,
                },
            )

        # Notify participants about status change.
        participant_users = MeetingParticipant.objects.filter(
            meeting_id=meeting
        ).exclude(user_id=meeting.task_id.assigned_to).select_related("user_id")
        for p in participant_users:
            if p.user_id != request.user:
                trigger_notification_event(
                    event_type=NotificationEventType.MEETING_STATUS_CHANGED,
                    recipient=p.user_id,
                    context={
                        "user_name": p.user_id.get_full_name() or p.user_id.username,
                        "employee_name": request.user.get_full_name() or request.user.username,
                        "meeting_title": meeting.meeting_title,
                        "old_status": old_status.status_name,
                        "new_status": new_status.status_name,
                    },
                )

        return Response(
            {
                "message": "Meeting status updated successfully.",
                "meeting_id": meeting.meeting_id,
                "previous_status": old_status.status_name,
                "new_status": new_status.status_name
            },
            status=status.HTTP_200_OK
        )


# ==========================================================
# ADD MEETING PARTICIPANT
# ==========================================================

class MeetingParticipantAddView(APIView):
    """
    POST /api/meetings/<meeting_id>/participants/

    Add a participant.
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "POST": "add_meetingparticipant",
    }

    def post(self, request, meeting_id):

        meeting = get_object_or_404(
            Meeting,
            meeting_id=meeting_id
        )

        user_id = request.data.get("user_id")
        participant_role = request.data.get(
            "participant_role"
        )
        is_required = request.data.get(
            "is_required",
            True
        )

        if not user_id:

            return Response(
                {
                    "user_id": "This field is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not participant_role:

            return Response(
                {
                    "participant_role": (
                        "This field is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(
            User,
            pk=user_id
        )

        # Prevent duplicate participant
        already_exists = MeetingParticipant.objects.filter(
            meeting_id=meeting,
            user_id=user
        ).exists()

        if already_exists:

            return Response(
                {
                    "error": (
                        "This user is already a participant "
                        "of this meeting."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        participant = MeetingParticipant.objects.create(
            meeting_id=meeting,
            user_id=user,
            participant_role=participant_role.strip(),
            is_required=is_required
        )

        # Notify the added participant.
        if user != request.user:
            trigger_notification_event(
                event_type=NotificationEventType.MEETING_PARTICIPANT_ADDED,
                recipient=user,
                context={
                    "user_name": user.get_full_name() or user.username,
                    "employee_name": request.user.get_full_name() or request.user.username,
                    "meeting_title": meeting.meeting_title,
                    "meeting_date": str(meeting.meeting_date),
                    "participant_role": participant_role.strip(),
                },
            )

        # Notify the meeting creator about the new participant.
        if meeting.created_by and meeting.created_by != request.user and meeting.created_by != user:
            trigger_notification_event(
                event_type=NotificationEventType.MEETING_PARTICIPANT_ADDED,
                recipient=meeting.created_by,
                context={
                    "user_name": meeting.created_by.get_full_name() or meeting.created_by.username,
                    "employee_name": request.user.get_full_name() or request.user.username,
                    "meeting_title": meeting.meeting_title,
                    "meeting_date": str(meeting.meeting_date),
                    "participant_name": user.get_full_name() or user.username,
                    "participant_role": participant_role.strip(),
                },
            )

        serializer = MeetingParticipantSerializer(
            participant,
            context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )


# ==========================================================
# REMOVE MEETING PARTICIPANT
# ==========================================================

class MeetingParticipantRemoveView(APIView):
    """
    DELETE /api/meetings/<meeting_id>/participants/<user_id>/

    Remove participant from meeting.
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "DELETE": "delete_meetingparticipant",
    }

    def delete(self, request, meeting_id, user_id):

        meeting = get_object_or_404(
            Meeting,
            meeting_id=meeting_id
        )

        participant = get_object_or_404(
            MeetingParticipant,
            meeting_id=meeting,
            user_id_id=user_id
        )

        removed_user = participant.user_id
        participant.delete()

        # Notify the removed participant.
        if removed_user and removed_user != request.user:
            trigger_notification_event(
                event_type=NotificationEventType.MEETING_PARTICIPANT_REMOVED,
                recipient=removed_user,
                context={
                    "user_name": removed_user.get_full_name() or removed_user.username,
                    "employee_name": request.user.get_full_name() or request.user.username,
                    "meeting_title": meeting.meeting_title,
                    "meeting_date": str(meeting.meeting_date),
                },
            )

        # Notify the meeting creator about the removal.
        if meeting.created_by and meeting.created_by != request.user and meeting.created_by != removed_user:
            trigger_notification_event(
                event_type=NotificationEventType.MEETING_PARTICIPANT_REMOVED,
                recipient=meeting.created_by,
                context={
                    "user_name": meeting.created_by.get_full_name() or meeting.created_by.username,
                    "employee_name": request.user.get_full_name() or request.user.username,
                    "meeting_title": meeting.meeting_title,
                    "participant_name": removed_user.get_full_name() or removed_user.username if removed_user else "",
                },
            )

        return Response(
            {
                "message": "Participant removed successfully.",
                "meeting_id": meeting.meeting_id,
                "user_id": user_id
            },
            status=status.HTTP_200_OK
        )


# ==========================================================
# REMINDER
# ==========================================================

class ReminderCreateView(APIView):
    """
    POST /api/reminders/

    Create a reminder.
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "POST": "add_reminder",
    }

    def post(self, request):

        serializer = ReminderSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():

            reminder = serializer.save(
                created_by=request.user
            )

            # Notify the creator about the reminder.
            trigger_notification_event(
                event_type=NotificationEventType.REMINDER_CREATED,
                recipient=request.user,
                context={
                    "user_name": request.user.get_full_name() or request.user.username,
                    "reminder_message": reminder.message,
                    "reminder_datetime": str(reminder.reminder_datetime),
                },
            )

            # Notify assigned user on the related task (if different).
            if reminder.task_id and reminder.task_id.assigned_to and reminder.task_id.assigned_to != request.user:
                trigger_notification_event(
                    event_type=NotificationEventType.REMINDER_CREATED,
                    recipient=reminder.task_id.assigned_to,
                    context={
                        "user_name": reminder.task_id.assigned_to.get_full_name() or reminder.task_id.assigned_to.username,
                        "employee_name": request.user.get_full_name() or request.user.username,
                        "reminder_message": reminder.message,
                        "reminder_datetime": str(reminder.reminder_datetime),
                    },
                )

            return Response(
                ReminderSerializer(
                    reminder,
                    context={"request": request}
                ).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class ReminderDetailView(APIView):
    """
    GET    /api/reminders/<reminder_id>/
        Reminder detail

    PATCH  /api/reminders/<reminder_id>/
        Update reminder

    DELETE /api/reminders/<reminder_id>/
        Delete reminder
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "GET": "view_reminder",
        "PATCH": "change_reminder",
        "DELETE": "delete_reminder",
    }

    def get_reminder(self, reminder_id):

        return get_object_or_404(
            Reminder.objects.select_related(
                "task_id",
                "meeting_id",
                "reminder_type_id",
                "reminder_status_id",
                "created_by",
            ),
            reminder_id=reminder_id
        )

    # ------------------------------------------------------
    # REMINDER DETAIL
    # ------------------------------------------------------

    def get(self, request, reminder_id):

        reminder = self.get_reminder(reminder_id)

        serializer = ReminderSerializer(
            reminder,
            context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    # ------------------------------------------------------
    # UPDATE REMINDER
    # ------------------------------------------------------

    def patch(self, request, reminder_id):

        reminder = self.get_reminder(reminder_id)

        serializer = ReminderSerializer(
            reminder,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():

            reminder = serializer.save()

            # Notify the creator about the reminder update.
            trigger_notification_event(
                event_type=NotificationEventType.REMINDER_UPDATED,
                recipient=request.user,
                context={
                    "user_name": request.user.get_full_name() or request.user.username,
                    "reminder_message": reminder.message,
                    "reminder_datetime": str(reminder.reminder_datetime),
                },
            )

            return Response(
                ReminderSerializer(
                    reminder,
                    context={"request": request}
                ).data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # ------------------------------------------------------
    # DELETE REMINDER
    # ------------------------------------------------------

    def delete(self, request, reminder_id):

        reminder = self.get_reminder(reminder_id)

        # Notify the creator about the reminder deletion.
        trigger_notification_event(
            event_type=NotificationEventType.REMINDER_DELETED,
            recipient=request.user,
            context={
                "user_name": request.user.get_full_name() or request.user.username,
                "reminder_message": reminder.message,
            },
        )

        # Notify assigned user on the related task (if different).
        if reminder.task_id and reminder.task_id.assigned_to and reminder.task_id.assigned_to != request.user:
            trigger_notification_event(
                event_type=NotificationEventType.REMINDER_DELETED,
                recipient=reminder.task_id.assigned_to,
                context={
                    "user_name": reminder.task_id.assigned_to.get_full_name() or reminder.task_id.assigned_to.username,
                    "employee_name": request.user.get_full_name() or request.user.username,
                    "reminder_message": reminder.message,
                },
            )

        # Your Reminder model does not have is_active,
        # so with the current model this is a real delete.
        reminder.delete()

        return Response(
            {
                "message": "Reminder deleted successfully.",
                "reminder_id": reminder_id
            },
            status=status.HTTP_200_OK
        )


# ==========================================================
# CHANGE REMINDER STATUS
# ==========================================================

class ReminderStatusUpdateView(APIView):
    """
    PATCH /api/reminders/<reminder_id>/status/

    Change reminder status.
    """

    permission_classes = [TaskHasPermission]

    permission_names = {
        "PATCH": "change_reminder",
    }

    def patch(self, request, reminder_id):

        reminder = get_object_or_404(
            Reminder,
            reminder_id=reminder_id
        )

        status_id = request.data.get(
            "reminder_status_id"
        )

        if not status_id:

            return Response(
                {
                    "reminder_status_id": (
                        "This field is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        new_status = get_object_or_404(
            ReminderStatus,
            reminder_status_id=status_id,
            is_active=True
        )

        old_status = reminder.reminder_status_id

        reminder.reminder_status_id = new_status

        reminder.save(
            update_fields=[
                "reminder_status_id",
                "updated_at"
            ]
        )

        # Notify the creator about the reminder status change.
        trigger_notification_event(
            event_type=NotificationEventType.REMINDER_STATUS_CHANGED,
            recipient=request.user,
            context={
                "user_name": request.user.get_full_name() or request.user.username,
                "reminder_message": reminder.message,
                "old_status": old_status.status_name,
                "new_status": new_status.status_name,
            },
        )

        # Notify assigned user on the related task (if different).
        if reminder.task_id and reminder.task_id.assigned_to and reminder.task_id.assigned_to != request.user:
            trigger_notification_event(
                event_type=NotificationEventType.REMINDER_STATUS_CHANGED,
                recipient=reminder.task_id.assigned_to,
                context={
                    "user_name": reminder.task_id.assigned_to.get_full_name() or reminder.task_id.assigned_to.username,
                    "employee_name": request.user.get_full_name() or request.user.username,
                    "reminder_message": reminder.message,
                    "old_status": old_status.status_name,
                    "new_status": new_status.status_name,
                },
            )

        return Response(
            {
                "message": (
                    "Reminder status updated successfully."
                ),
                "reminder_id": reminder.reminder_id,
                "previous_status": old_status.status_name,
                "new_status": new_status.status_name
            },
            status=status.HTTP_200_OK
        )
