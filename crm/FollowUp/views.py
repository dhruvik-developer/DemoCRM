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

from Notification.notification_utils import (
    trigger_notification_event,
)
from Notification.models import NotificationEventType

from .serializers import (
    FollowupSerializer,
    FollowUpNoteSerializer,
)


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

        recipient = followup.task_id.assigned_to if followup.task_id and followup.task_id.assigned_to else request.user
        trigger_notification_event(
            event_type=NotificationEventType.FOLLOWUP_CREATED,
            recipient=recipient,
            context={
                "user_name": recipient.get_full_name() or recipient.username,
                "followup_date": str(followup.followup_date),
                "task_title": followup.task_id.task_title if followup.task_id else "",
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

        if followup.followup_status and followup.followup_status.status_name.upper() in ["COMPLETED", "COMPLETE", "DONE"]:
            recipient = followup.created_by or (followup.task_id.assigned_to if followup.task_id else request.user)
            trigger_notification_event(
                event_type=NotificationEventType.FOLLOWUP_COMPLETED,
                recipient=recipient,
                context={
                    "employee_name": request.user.get_full_name() or request.user.username,
                    "followup_date": str(followup.followup_date),
                    "task_title": followup.task_id.task_title if followup.task_id else "",
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

        return Response(
            FollowUpNoteSerializer(
                note,
                context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED
        )


