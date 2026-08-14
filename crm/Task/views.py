from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts import serializers    
from .services import send_meeting_reminder_email, send_meeting_creation_emails
from .models import (
    MeetingType,
    ReminderType,
    Task,
    TaskStatus,
    Meeting,
    MeetingStatus,
    MeetingParticipant,
    Reminder,
    ReminderStatus,
)

from .serializers import (
    MeetingTypeSerializer,
    ReminderStatusSerializer,
    ReminderTypeSerializer,
    TaskSerializer,
    MeetingSerializer,
    MeetingStatusSerializer,
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

# ============================================================
# MEETING STATUS
# ============================================================

class MeetingStatusViewSet(viewsets.ModelViewSet):

    queryset = MeetingStatus.objects.all().order_by(
        "meeting_status_id"
    )

    serializer_class = MeetingStatusSerializer
    permission_classes = [IsAuthenticated]


# ============================================================
# MEETING TYPE
# ============================================================

class MeetingTypeViewSet(viewsets.ModelViewSet):

    queryset = MeetingType.objects.all().order_by(
        "meeting_type_id"
    )

    serializer_class = MeetingTypeSerializer
    permission_classes = [IsAuthenticated]


# ============================================================
# MEETING
# ============================================================

class MeetingViewSet(viewsets.ModelViewSet):

    queryset = Meeting.objects.select_related(
        "task_id",
        "lead",
        "meeting_status_id",
        "meeting_type_id",
        "created_by",
    ).prefetch_related(
        "participants",
        "reminders",
    ).all().order_by("-meeting_date", "-start_time")

    serializer_class = MeetingSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):

        meeting = serializer.save(
            created_by=self.request.user
        )

        # Send meeting email to both Lead and Host/Creator, and create DB reminder
        send_meeting_creation_emails(meeting)

    def get_queryset(self):

        queryset = super().get_queryset()

        task_id = self.request.query_params.get("task_id")
        lead_id = self.request.query_params.get("lead")
        meeting_status = self.request.query_params.get(
            "meeting_status"
        )
        meeting_type = self.request.query_params.get(
            "meeting_type"
        )
        created_by = self.request.query_params.get(
            "created_by"
        )

        if task_id:
            queryset = queryset.filter(
                task_id_id=task_id
            )

        if lead_id:
            queryset = queryset.filter(
                lead_id=lead_id
            )

        if meeting_status:
            queryset = queryset.filter(
                meeting_status_id_id=meeting_status
            )

        if meeting_type:
            queryset = queryset.filter(
                meeting_type_id_id=meeting_type
            )

        if created_by:
            queryset = queryset.filter(
                created_by_id=created_by
            )

        return queryset


# ============================================================
# MEETING PARTICIPANT
# ============================================================

class MeetingParticipantViewSet(viewsets.ModelViewSet):

    queryset = MeetingParticipant.objects.select_related(
        "meeting_id",
        "user_id",
    ).all().order_by("participant_id")

    serializer_class = MeetingParticipantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        queryset = super().get_queryset()

        meeting_id = self.request.query_params.get(
            "meeting_id"
        )

        user_id = self.request.query_params.get(
            "user_id"
        )

        if meeting_id:
            queryset = queryset.filter(
                meeting_id_id=meeting_id
            )

        if user_id:
            queryset = queryset.filter(
                user_id_id=user_id
            )

        return queryset


# ============================================================
# REMINDER TYPE
# ============================================================

class ReminderTypeViewSet(viewsets.ModelViewSet):

    queryset = ReminderType.objects.all().order_by(
        "reminder_type_id"
    )

    serializer_class = ReminderTypeSerializer
    permission_classes = [IsAuthenticated]


# ============================================================
# REMINDER STATUS
# ============================================================

class ReminderStatusViewSet(viewsets.ModelViewSet):

    queryset = ReminderStatus.objects.all().order_by(
        "reminder_status_id"
    )

    serializer_class = ReminderStatusSerializer
    permission_classes = [IsAuthenticated]


# ============================================================
# REMINDER
# ============================================================

class ReminderViewSet(viewsets.ModelViewSet):

    queryset = Reminder.objects.select_related(
        "task_id",
        "meeting_id",
        "reminder_for",
        "reminder_type_id",
        "reminder_status_id",
        "created_by",
    ).all().order_by("reminder_datetime")

    serializer_class = ReminderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):

        serializer.save(
            created_by=self.request.user
        )

    def get_queryset(self):

        queryset = super().get_queryset()

        meeting_id = self.request.query_params.get(
            "meeting_id"
        )

        task_id = self.request.query_params.get(
            "task_id"
        )

        reminder_for = self.request.query_params.get(
            "reminder_for"
        )

        is_sent = self.request.query_params.get(
            "is_sent"
        )

        if meeting_id:
            queryset = queryset.filter(
                meeting_id_id=meeting_id
            )

        if task_id:
            queryset = queryset.filter(
                task_id_id=task_id
            )

        if reminder_for:
            queryset = queryset.filter(
                reminder_for_id=reminder_for
            )

        if is_sent is not None:
            queryset = queryset.filter(
                is_sent=is_sent.lower() == "true"
            )

        return queryset