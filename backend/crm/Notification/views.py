import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
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

    @extend_schema(
        tags=["Notification Templates"],
        summary="List notification templates",
        description="GET: List all notification templates with optional filtering by event_type and is_active. Requires view_notification_template permission.",
        operation_id="notification_template_list",
        parameters=[
            OpenApiParameter(
                name="event_type",
                type=str,
                description="Filter templates by event type (e.g. TASK_ASSIGNED, LEAD_CREATED)",
                required=False,
            ),
            OpenApiParameter(
                name="is_active",
                type=bool,
                description="Filter templates by active status",
                required=False,
            ),
        ],
        responses={
            200: NotificationTemplateSerializer(many=True),
            500: inline_serializer(
                "NotificationTemplateListServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
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

    @extend_schema(
        tags=["Notification Templates"],
        summary="Create a notification template",
        description="POST: Create a new notification template. Requires add_notification_template permission.",
        operation_id="notification_template_create",
        request=NotificationTemplateSerializer,
        responses={
            201: NotificationTemplateSerializer,
            400: NotificationTemplateSerializer,
            500: inline_serializer(
                "NotificationTemplateCreateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
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

    @extend_schema(
        tags=["Notification Templates"],
        summary="Retrieve a notification template",
        description="GET: Retrieve details of a specific notification template. Requires view_notification_template permission.",
        operation_id="notification_template_retrieve",
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Template ID",
            ),
        ],
        responses={
            200: NotificationTemplateSerializer,
            404: inline_serializer(
                "NotificationTemplateNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "NotificationTemplateRetrieveServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
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

    @extend_schema(
        tags=["Notification Templates"],
        summary="Update a notification template",
        description="PUT: Fully update a notification template. Requires change_notification_template permission.",
        operation_id="notification_template_update",
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Template ID",
            ),
        ],
        request=NotificationTemplateSerializer,
        responses={
            200: NotificationTemplateSerializer,
            400: NotificationTemplateSerializer,
            404: inline_serializer(
                "NotificationTemplateUpdateNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "NotificationTemplateUpdateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
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

    @extend_schema(
        tags=["Notification Templates"],
        summary="Partially update a notification template",
        description="PATCH: Partially update a notification template. Requires change_notification_template permission.",
        operation_id="notification_template_partial_update",
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Template ID",
            ),
        ],
        request=NotificationTemplateSerializer,
        responses={
            200: NotificationTemplateSerializer,
            400: NotificationTemplateSerializer,
            404: inline_serializer(
                "NotificationTemplatePartialUpdateNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "NotificationTemplatePartialUpdateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
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

    @extend_schema(
        tags=["Notification Templates"],
        summary="Deactivate a notification template",
        description="DELETE: Soft-delete a notification template by setting is_active=False. Requires delete_notification_template permission.",
        operation_id="notification_template_delete",
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Template ID",
            ),
        ],
        responses={
            200: inline_serializer(
                "NotificationTemplateDeleteSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "template_id": serializers.IntegerField(),
                },
            ),
            404: inline_serializer(
                "NotificationTemplateDeleteNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "NotificationTemplateDeleteServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
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

    @extend_schema(
        tags=["Notifications"],
        summary="Send a manual notification",
        description="POST: Send a manual notification to one or more recipients, optionally using a template or custom message. Requires send_manual_notification permission.",
        operation_id="notification_send_manual",
        request=ManualNotificationSerializer,
        responses={
            201: NotificationSerializer(many=True),
            400: ManualNotificationSerializer,
            500: inline_serializer(
                "NotificationSendServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
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

    # Ownership is enforced by the recipient filter below; no role codename
    # is required for a user to read their own notifications.
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="List my notifications",
        description="GET: List notifications belonging strictly to the currently authenticated user, with optional is_read filter. Requires view_notification permission.",
        operation_id="user_notification_list",
        parameters=[
            OpenApiParameter(
                name="is_read",
                type=bool,
                description="Filter notifications by read status",
                required=False,
            ),
        ],
        responses={
            200: NotificationSerializer(many=True),
            500: inline_serializer(
                "UserNotificationListServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
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

            # Pagination: ?page=1&page_size=10 (default 10, max 50) — avoids infinite scroll
            from django.core.paginator import EmptyPage, Paginator

            try:
                page = int(request.query_params.get("page", "1"))
            except ValueError:
                page = 1
            try:
                page_size = int(request.query_params.get("page_size", "20"))
            except ValueError:
                page_size = 20
            page_size = max(1, min(page_size, 50))
            paginator = Paginator(notifications, page_size)
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                page_obj = (
                    paginator.page(paginator.num_pages) if paginator.num_pages else []
                )

            serializer = NotificationSerializer(
                page_obj.object_list if hasattr(page_obj, "object_list") else [],
                many=True,
            )
            return Response(
                {
                    "count": paginator.count,
                    "num_pages": paginator.num_pages,
                    "page": page,
                    "page_size": page_size,
                    "results": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
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

    # Ownership is enforced by the recipient filter in the queryset.
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Retrieve my notification",
        description="GET: Retrieve a specific notification belonging to the authenticated user. Requires view_notification permission.",
        operation_id="user_notification_retrieve",
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Notification ID",
            ),
        ],
        responses={
            200: NotificationSerializer,
            404: inline_serializer(
                "UserNotificationNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "UserNotificationRetrieveServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
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

    # Ownership is enforced by the recipient filter in the queryset.
    permission_classes = [IsAuthenticated]

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

    @extend_schema(
        tags=["Notifications"],
        summary="Mark notification as read",
        description="PUT: Mark a notification as read for the authenticated recipient user. Requires change_notification permission.",
        operation_id="user_notification_mark_read",
        request=None,
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Notification ID",
            ),
        ],
        responses={
            200: NotificationSerializer,
            404: inline_serializer(
                "UserNotificationMarkReadNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "UserNotificationMarkReadServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def put(self, request, pk):
        return self._mark_read(request, pk)

    @extend_schema(
        tags=["Notifications"],
        summary="Mark notification as read (partial)",
        description="PATCH: Mark a notification as read for the authenticated recipient user. Requires change_notification permission.",
        operation_id="user_notification_mark_read_partial",
        request=None,
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Notification ID",
            ),
        ],
        responses={
            200: NotificationSerializer,
            404: inline_serializer(
                "UserNotificationMarkReadPartialNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "UserNotificationMarkReadPartialServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def patch(self, request, pk):
        return self._mark_read(request, pk)
