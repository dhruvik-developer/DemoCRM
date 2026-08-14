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
    Notification,
    NotificationTemplate,
)

from .notification_utils import (
    create_notification,
    send_notification_email,
)

from .serializers import (
    FollowupSerializer,
    FollowUpNoteSerializer,
    NotificationSendSerializer,
    NotificationSerializer,
    NotificationTemplateSerializer,
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


# ==========================================================
# NOTIFICATION
# ==========================================================

class UserNotificationListView(APIView):
    """
    GET /api/notifications/

    Return notifications belonging to the
    currently authenticated user.
    """

    permission_classes = [FollowUpHasPermission]

    permission_names = {
        "GET": "view_notification",
    }

    def get(self, request):

        notifications = (
            Notification.objects
            .select_related(
                "notification_type_id",
                "template_id",
                "user_id",
            )
            .filter(
                user_id=request.user
            )
            .order_by("-created_at")
        )

        serializer = NotificationSerializer(
            notifications,
            many=True,
            context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class NotificationDetailView(APIView):
    """
    GET /api/notifications/<notification_id>/

    Return one notification belonging to
    the authenticated user.
    """

    permission_classes = [FollowUpHasPermission]

    permission_names = {
        "GET": "view_notification",
    }

    def get(self, request, notification_id):

        notification = get_object_or_404(
            Notification.objects.select_related(
                "notification_type_id",
                "template_id",
                "user_id",
            ),
            notification_id=notification_id,
            user_id=request.user
        )

        serializer = NotificationSerializer(
            notification,
            context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


# ==========================================================
# NOTIFICATION TEMPLATES / PREVIEW / SEND
# ==========================================================

class NotificationTemplateListView(APIView):
    """
    GET /api/followups/notification-templates/

    List active notification templates.
    Optional ?type=<notification_type_id> filter.
    """

    permission_classes = [FollowUpHasPermission]

    permission_names = {
        "GET": "view_notificationtemplate",
    }

    def get(self, request):

        templates = NotificationTemplate.objects.filter(
            is_active=True,
        ).select_related("notification_type_id").order_by("template_id")

        type_id = request.query_params.get("type")
        if type_id:
            templates = templates.filter(notification_type_id=type_id)

        serializer = NotificationTemplateSerializer(
            templates,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class NotificationPreviewView(APIView):
    """
    POST /api/followups/notifications/preview/

    Generate the message from a template + context so the
    admin/manager can review and edit it before sending.

    Request body:
    {
        "recipients": ["<user-uuid>", ...],
        "template_id": 1,
        "task_id": 2,            # optional, for placeholders
        "followup_id": 3,        # optional, for placeholders
        "message": "..."         # optional, custom override
    }
    """

    permission_classes = [FollowUpHasPermission]

    permission_names = {
        "POST": "view_notificationtemplate",
    }

    def post(self, request):

        serializer = NotificationSendSerializer(
            data=request.data,
            context={"request": request}
        )

        if not serializer.is_valid():

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        subject, body = serializer.rendered()

        return Response(
            {
                "template_id": serializer.validated_data["template_id"].template_id,
                "subject": subject,
                "body": body,
                "recipients": [
                    str(user.user_id)
                    for user in serializer.validated_data["recipients"]
                ],
                "message_editable": self.can_customize(request.user),
            },
            status=status.HTTP_200_OK
        )

    def can_customize(self, user):
        return (
            user.is_superuser
            or (user.role is not None and user.role.rolename in ["Admin", "Manager"])
        )


class NotificationSendView(APIView):
    """
    POST /api/followups/notifications/send/

    Send (or schedule) a notification for one or many recipients.

    Request body:
    {
        "recipients": ["<user-uuid>", ...],
        "template_id": 1,
        "notification_type_id": 1,   # optional
        "task_id": 2,                # optional, placeholder context
        "followup_id": 3,            # optional, placeholder context
        "message": "..."             # optional custom message (Admin/Manager only)
        "scheduled_at": null         # optional future datetime
    }
    """

    permission_classes = [FollowUpHasPermission]

    permission_names = {
        "POST": "send_notification",
    }

    def post(self, request):

        serializer = NotificationSendSerializer(
            data=request.data,
            context={"request": request}
        )

        if not serializer.is_valid():

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        subject, body = serializer.rendered()

        customized = bool(data.get("message"))

        if customized and not self.can_customize(request.user):

            return Response(
                {
                    "error": (
                        "Only Admin and Manager can customize the message."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        notification_type = serializer.notification_type()
        template = data["template_id"]
        scheduled_at = data.get("scheduled_at")

        created_notifications = []

        for recipient in data["recipients"]:

            notification = create_notification(
                user=recipient,
                title=subject,
                message=body,
                type_name=notification_type.type_name,
                template=template,
                scheduled_at=scheduled_at,
                edited_by=request.user if customized else None,
                is_customized=customized,
            )

            if not scheduled_at:
                send_notification_email(notification)

            created_notifications.append(notification)

        return Response(
            NotificationSerializer(
                created_notifications,
                many=True,
                context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED
        )

    def can_customize(self, user):
        return (
            user.is_superuser
            or (user.role is not None and user.role.rolename in ["Admin", "Manager"])
        )