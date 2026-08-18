import logging

from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import FollowUpHasPermission

from .models import (
    Followup,
    FollowUpNote,
)


from .serializers import (
    FollowupSerializer,
    FollowUpNoteSerializer,
)

from Notification.notification_utils import trigger_notification_event
from Notification.models import NotificationEventType


# ==========================================================
# FOLLOWUP
# ==========================================================

class FollowUpListCreateView(APIView):
    """
    GET  /api/followups/
        List FollowUps

    POST /api/followups/
        Create FollowUp
    """

    permission_classes = [FollowUpHasPermission]

    permission_names = {
        "GET": "view_followup",
        "POST": "add_followup",
    }

    # ------------------------------------------------------
    # LIST FOLLOWUPS
    # ------------------------------------------------------

    def get(self, request):

        followups = (
            Followup.objects
            .select_related(
                "task_id",
                "followup_status",
                "followup_type",
                "created_by",
            )
            .order_by("-created_at")
        )

        serializer = FollowupSerializer(
            followups,
            many=True,
            context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    # ------------------------------------------------------
    # CREATE FOLLOWUP
    # ------------------------------------------------------

    def post(self, request):

        serializer = FollowupSerializer(
            data=request.data,
            context={"request": request}
        )

        if not serializer.is_valid():

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # created_by MUST come from authenticated user.
        # Do not trust created_by from frontend.
        followup = serializer.save(
            created_by=request.user
        )

        # Notify the task assignee about the followup.
        if followup.task_id and followup.task_id.assigned_to and followup.task_id.assigned_to != request.user:
            trigger_notification_event(
                event_type=NotificationEventType.FOLLOWUP_CREATED,
                recipient=followup.task_id.assigned_to,
                context={
                    "user_name": followup.task_id.assigned_to.get_full_name() or followup.task_id.assigned_to.username,
                    "employee_name": request.user.get_full_name() or request.user.username,
                    "task_title": followup.task_id.task_title,
                    "followup_date": str(followup.followup_date),
                },
            )

        logger.info("FollowUp created for task %s by user %s (ID: %s)", followup.task_id_id, request.user.user_id, followup.followup_id)

        return Response(
            FollowupSerializer(
                followup,
                context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED
        )


# ==========================================================
# FOLLOWUP DETAIL / UPDATE / DELETE
# ==========================================================

class FollowUpDetailView(APIView):
    """
    GET    /api/followups/<followup_id>/
        FollowUp Detail

    PATCH  /api/followups/<followup_id>/
        Update FollowUp

    DELETE /api/followups/<followup_id>/
        Delete FollowUp
    """

    permission_classes = [FollowUpHasPermission]

    permission_names = {
        "GET": "view_followup",
        "PATCH": "change_followup",
        "DELETE": "delete_followup",
    }

    def get_followup(self, followup_id):

        return get_object_or_404(
            Followup.objects.select_related(
                "task_id",
                "followup_status",
                "followup_type",
                "created_by",
            ),
            followup_id=followup_id
        )

    # ------------------------------------------------------
    # DETAIL
    # ------------------------------------------------------

    def get(self, request, followup_id):

        followup = self.get_followup(followup_id)

        serializer = FollowupSerializer(
            followup,
            context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    # ------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------

    def patch(self, request, followup_id):

        followup = self.get_followup(followup_id)

        serializer = FollowupSerializer(
            followup,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if not serializer.is_valid():

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        followup = serializer.save()

        # Notify the task assignee about the followup update.
        if followup.task_id and followup.task_id.assigned_to and followup.task_id.assigned_to != request.user:
            trigger_notification_event(
                event_type=NotificationEventType.FOLLOWUP_UPDATED,
                recipient=followup.task_id.assigned_to,
                context={
                    "user_name": followup.task_id.assigned_to.get_full_name() or followup.task_id.assigned_to.username,
                    "employee_name": request.user.get_full_name() or request.user.username,
                    "task_title": followup.task_id.task_title,
                    "followup_date": str(followup.followup_date),
                },
            )

        return Response(
            FollowupSerializer(
                followup,
                context={"request": request}
            ).data,
            status=status.HTTP_200_OK
        )

    # ------------------------------------------------------
    # DELETE
    # ------------------------------------------------------

    def delete(self, request, followup_id):

        followup = self.get_followup(followup_id)

        # Notify the task assignee about the followup deletion.
        if followup.task_id and followup.task_id.assigned_to and followup.task_id.assigned_to != request.user:
            trigger_notification_event(
                event_type=NotificationEventType.FOLLOWUP_DELETED,
                recipient=followup.task_id.assigned_to,
                context={
                    "user_name": followup.task_id.assigned_to.get_full_name() or followup.task_id.assigned_to.username,
                    "employee_name": request.user.get_full_name() or request.user.username,
                    "task_title": followup.task_id.task_title,
                },
            )

        # IMPORTANT:
        # Your Followup model does NOT have is_active.
        # Therefore this is a real delete.
        followup.delete()

        return Response(
            {
                "message": "FollowUp deleted successfully.",
                "followup_id": followup_id
            },
            status=status.HTTP_200_OK
        )


# ==========================================================
# FOLLOWUP NOTE
# ==========================================================

class FollowUpNoteCreateView(APIView):
    """
    POST /api/followups/<followup_id>/notes/

    Add a note to a FollowUp.
    """

    permission_classes = [FollowUpHasPermission]

    permission_names = {
        "POST": "add_followupnote",
    }

    def post(self, request, followup_id):

        followup = get_object_or_404(
            Followup,
            followup_id=followup_id
        )

        serializer = FollowUpNoteSerializer(
            data=request.data,
            context={"request": request}
        )

        if not serializer.is_valid():

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # followup_id and created_by should come from backend.
        note = serializer.save(
            followup_id=followup,
            created_by=request.user
        )

        # Notify the task assignee about the new note.
        if followup.task_id and followup.task_id.assigned_to and followup.task_id.assigned_to != request.user:
            trigger_notification_event(
                event_type=NotificationEventType.FOLLOWUP_NOTE_ADDED,
                recipient=followup.task_id.assigned_to,
                context={
                    "user_name": followup.task_id.assigned_to.get_full_name() or followup.task_id.assigned_to.username,
                    "employee_name": request.user.get_full_name() or request.user.username,
                    "task_title": followup.task_id.task_title,
                    "note_preview": (note.note[:100] + "...") if len(note.note) > 100 else note.note,
                },
            )

        # Notify the followup creator about the new note (if different from task assignee).
        if followup.created_by and followup.created_by != request.user:
            if not (followup.task_id and followup.task_id.assigned_to and followup.task_id.assigned_to == followup.created_by):
                trigger_notification_event(
                    event_type=NotificationEventType.FOLLOWUP_NOTE_ADDED,
                    recipient=followup.created_by,
                    context={
                        "user_name": followup.created_by.get_full_name() or followup.created_by.username,
                        "employee_name": request.user.get_full_name() or request.user.username,
                        "task_title": followup.task_id.task_title,
                        "note_preview": (note.note[:100] + "...") if len(note.note) > 100 else note.note,
                    },
                )

        return Response(
            FollowUpNoteSerializer(
                note,
                context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED
        )


