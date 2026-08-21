import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, NotificationTemplate
from .permissions import NotificationHasPermission
from .serializers import (
    ManualNotificationSerializer,
    NotificationSerializer,
    NotificationTemplateSerializer,
)
from .notification_utils import trigger_notification_event

logger = logging.getLogger(__name__)


# ==========================================================
# TEMPLATE MANAGEMENT VIEWS (APIView ONLY)
# ==========================================================


class NotificationTemplateListView(APIView):
    """
    GET  /notification-templates/
        List notification templates (supports ?event_type= filter)

    POST /notification-templates/
        Create a new notification template
    """

    permission_classes = [NotificationHasPermission]

    permission_names = {
        "GET": "view_notification_template",
        "POST": "add_notification_template",
    }

    def get(self, request):
        try:
            templates = NotificationTemplate.objects.all()

            event_type = request.query_params.get("event_type")
            if event_type:
                templates = templates.filter(event_type=event_type)

            is_active = request.query_params.get("is_active")
            if is_active is not None:
                active_bool = is_active.lower() in ("true", "1")
                templates = templates.filter(is_active=active_bool)

            serializer = NotificationTemplateSerializer(templates, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to list notification templates: %s", e)
            return Response(
                {"error": "Failed to retrieve notification templates."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        try:
            serializer = NotificationTemplateSerializer(data=request.data)
            if serializer.is_valid():
                template = serializer.save()
                logger.info(
                    "NotificationTemplate created: %s (ID: %s)",
                    template.name,
                    template.pk,
                )
                return Response(
                    NotificationTemplateSerializer(template).data,
                    status=status.HTTP_201_CREATED,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to create notification template: %s", e)
            return Response(
                {"error": "Failed to create notification template."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NotificationTemplateDetailView(APIView):
    """
    GET    /notification-templates/{id}/
        Retrieve template detail

    PUT    /notification-templates/{id}/
        Update template

    PATCH  /notification-templates/{id}/
        Partial update template

    DELETE /notification-templates/{id}/
        Soft delete template (is_active=False)
    """

    permission_classes = [NotificationHasPermission]

    permission_names = {
        "GET": "view_notification_template",
        "PUT": "change_notification_template",
        "PATCH": "change_notification_template",
        "DELETE": "delete_notification_template",
    }

    def get_template(self, pk):
        return get_object_or_404(NotificationTemplate, pk=pk)

    def get(self, request, pk):
        try:
            template = self.get_template(pk)
            serializer = NotificationTemplateSerializer(template)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to retrieve notification template %s: %s", pk, e)
            return Response(
                {"error": "Failed to retrieve notification template."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, pk):
        try:
            template = self.get_template(pk)
            serializer = NotificationTemplateSerializer(template, data=request.data)
            if serializer.is_valid():
                template = serializer.save()
                return Response(
                    NotificationTemplateSerializer(template).data,
                    status=status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to update notification template %s: %s", pk, e)
            return Response(
                {"error": "Failed to update notification template."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def patch(self, request, pk):
        try:
            template = self.get_template(pk)
            serializer = NotificationTemplateSerializer(
                template, data=request.data, partial=True
            )
            if serializer.is_valid():
                template = serializer.save()
                return Response(
                    NotificationTemplateSerializer(template).data,
                    status=status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to update notification template %s: %s", pk, e)
            return Response(
                {"error": "Failed to update notification template."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, pk):
        try:
            template = self.get_template(pk)
            template.is_active = False
            template.save(update_fields=["is_active", "updated_at"])
            return Response(
                {
                    "message": "Notification template deactivated successfully.",
                    "template_id": template.pk,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error("Failed to delete notification template %s: %s", pk, e)
            return Response(
                {"error": "Failed to delete notification template."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# MANUAL NOTIFICATION SEND VIEW (APIView ONLY)
# ==========================================================


class ManualNotificationSendView(APIView):
    """
    POST /notifications/send/

    Send manual notification to one or more recipients.
    """

    permission_classes = [NotificationHasPermission]

    permission_names = {
        "POST": "send_manual_notification",
    }

    def post(self, request):
        try:
            serializer = ManualNotificationSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            validated_data = serializer.validated_data
            recipients = validated_data["recipients"]
            template_id = validated_data.get("template_id")
            event_type = validated_data.get("event_type") or "MANUAL"
            custom_message = validated_data.get("custom_message")
            channel = validated_data.get("channel")

            notifications = trigger_notification_event(
                event_type=event_type,
                recipient=recipients,
                template_id=template_id,
                custom_message=custom_message,
                channel=channel,
            )

            return Response(
                NotificationSerializer(notifications, many=True).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error("Failed to send manual notification: %s", e)
            return Response(
                {"error": "Failed to send notification."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# USER NOTIFICATION VIEWS (APIView ONLY)
# ==========================================================


class UserNotificationListView(APIView):
    """
    GET /notifications/

    Return notifications belonging strictly to the currently authenticated user.
    """

    permission_classes = [NotificationHasPermission]

    def get(self, request):
        try:
            notifications = (
                Notification.objects.filter(recipient=request.user)
                .select_related("template", "recipient")
                .order_by("-created_at")
            )

            is_read = request.query_params.get("is_read")
            if is_read is not None:
                read_bool = is_read.lower() in ("true", "1")
                notifications = notifications.filter(is_read=read_bool)

            serializer = NotificationSerializer(notifications, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "Failed to list notifications for user %s: %s", request.user, e
            )
            return Response(
                {"error": "Failed to retrieve notifications."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserNotificationDetailView(APIView):
    """
    GET /notifications/{id}/

    Return specific notification belonging to the authenticated user.
    """

    permission_classes = [NotificationHasPermission]

    def get(self, request, pk):
        try:
            notification = get_object_or_404(
                Notification.objects.select_related("template", "recipient"),
                pk=pk,
                recipient=request.user,
            )
            serializer = NotificationSerializer(notification)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to retrieve notification %s: %s", pk, e)
            return Response(
                {"error": "Failed to retrieve notification."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NotificationMarkReadView(APIView):
    """
    PUT   /notifications/{id}/read/
    PATCH /notifications/{id}/read/

    Mark notification as read for the authenticated recipient user.
    """

    permission_classes = [NotificationHasPermission]

    def _mark_read(self, request, pk):
        try:
            notification = get_object_or_404(
                Notification,
                pk=pk,
                recipient=request.user,
            )
            if not notification.is_read:
                notification.is_read = True
                notification.read_at = timezone.now()
                notification.save(update_fields=["is_read", "read_at"])

            serializer = NotificationSerializer(notification)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to mark notification %s as read: %s", pk, e)
            return Response(
                {"error": "Failed to mark notification as read."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, pk):
        return self._mark_read(request, pk)

    def patch(self, request, pk):
        return self._mark_read(request, pk)
