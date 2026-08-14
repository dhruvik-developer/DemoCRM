import logging

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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

    permission_classes = [IsAuthenticated]

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

            logger.info("Task created: %s (ID: %s) by user %s", task.title, task.task_id, request.user.user_id)

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

    permission_classes = [IsAuthenticated]

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

    permission_classes = [IsAuthenticated]

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

    permission_classes = [IsAuthenticated]

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

    permission_classes = [IsAuthenticated]

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

    permission_classes = [IsAuthenticated]

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

    permission_classes = [IsAuthenticated]

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

    permission_classes = [IsAuthenticated]

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

    permission_classes = [IsAuthenticated]

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

    permission_classes = [IsAuthenticated]

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

        participant.delete()

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

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = ReminderSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():

            reminder = serializer.save(
                created_by=request.user
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

    permission_classes = [IsAuthenticated]

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

    permission_classes = [IsAuthenticated]

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
