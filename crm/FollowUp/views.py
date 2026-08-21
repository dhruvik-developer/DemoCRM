import logging
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status, serializers
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Followup
from .serializers import (
    FollowupSerializer,
    FollowUpNoteSerializer,
)
from django.db.models import Q
from .pagination import CRMPageNumberPagination
from .permission import CanCommunicateWithlead
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from Notification.notification_utils import trigger_notification_event
from Notification.models import NotificationEventType

logger = logging.getLogger(__name__)


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

    permission_classes = [CanCommunicateWithlead]
    permission_names = {
        "GET": "view_followup",
        "POST": "add_followup",
    }

    # ------------------------------------------------------
    # LIST FOLLOWUPS
    # ------------------------------------------------------
    @extend_schema(
        tags=["Follow Ups"],
        summary="List follow-ups",
        description="GET: List all follow-ups with optional filtering, search, and pagination. Requires view_followup permission.",
        operation_id="followup_list",
        parameters=[
            OpenApiParameter(
                name="followup_status",
                type=int,
                description="Filter by follow-up status ID",
                required=False,
            ),
            OpenApiParameter(
                name="followup_type",
                type=int,
                description="Filter by follow-up type ID",
                required=False,
            ),
            OpenApiParameter(
                name="task_id",
                type=int,
                description="Filter by task ID",
                required=False,
            ),
            OpenApiParameter(
                name="created_by",
                type=int,
                description="Filter by creator user ID",
                required=False,
            ),
            OpenApiParameter(
                name="search",
                type=str,
                description="Search by description or task title",
                required=False,
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                description="Order results. Allowed fields: created_at, -created_at, updated_at, -updated_at",
                required=False,
                default="-created_at",
            ),
            OpenApiParameter(
                name="page", type=int, description="Page number", required=False
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                description="Results per page",
                required=False,
            ),
        ],
        responses={
            200: FollowupSerializer(many=True),
            500: inline_serializer(
                "FollowUpListServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def get(self, request):
        try:
            followups = (
                Followup.objects.filter(is_active=True)
                .select_related(
                    "task_id",
                    "followup_status",
                    "followup_type",
                    "created_by",
                )
                .order_by("-created_at")
            )
            # filter =========================================
            followup_status_id = request.query_params.get("followup_status")
            followup_type_id = request.query_params.get("followup_type")
            task_id = request.query_params.get("task_id")
            created_by_id = request.query_params.get("created_by")
            if followup_status_id:
                followups = followups.filter(followup_status_id=followup_status_id)
            if followup_type_id:
                followups = followups.filter(followup_type_id=followup_type_id)
            if task_id:
                followups = followups.filter(task_id=task_id)
            if created_by_id:
                followups = followups.filter(created_by_id=created_by_id)
            # search ==============================
            search = request.query_params.get("search")
            if search:
                followups = followups.filter(
                    Q(decription__icontains=search)
                    | Q(task_id__task_title__icontains=search)
                )
            # dynamic ordering =============================
            ordering = request.query_params.get("ordering", "-created_at")
            allowed_ordering_fields = {"created_at", "updated_at"}
            if ordering.lstrip("-") in allowed_ordering_fields:
                followups = followups.order_by(ordering)
            else:
                followups = followups.order_by("-created_at")
            # pagination =========================================
            paginator = CRMPageNumberPagination()
            paginator_followups = paginator.paginate_queryset(
                followups, request, view=self
            )
            serializer = FollowupSerializer(
                paginator_followups, many=True, context={"request": request}
            )
            logger.info(
                "FollowUps fetched successfully: user_id=%s page=%s",
                request.user.pk,
                request.query_params.get("page", 1),
            )
            return paginator.get_paginated_response(serializer.data)
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while fetching FollowUps: user_id=%s",
                request.user.pk,
            )
            return Response(
                {"error": "Something went wrong while fetching FollowUps."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------
    # CREATE FOLLOWUP
    # ------------------------------------------------------
    @extend_schema(
        tags=["Follow Ups"],
        summary="Create a follow-up",
        description="POST: Create a new follow-up. Requires add_followup permission.",
        operation_id="followup_create",
        request=FollowupSerializer,
        responses={
            201: FollowupSerializer,
            400: FollowupSerializer,
            500: inline_serializer(
                "FollowUpCreateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        try:
            serializer = FollowupSerializer(
                data=request.data, context={"request": request}
            )
            if not serializer.is_valid():
                logger.warning(
                    "FollowUp creation validation failed: user_id=%s errors=%s",
                    request.user.pk,
                    serializer.errors,
                )
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                followup = serializer.save(created_by=request.user)
            logger.info(
                "FollowUp created successfully: followup_id=%s user_id=%s",
                followup.followup_id,
                request.user.pk,
            )

            try:
                task = followup.task_id
                if task and task.assigned_to and task.assigned_to != request.user:
                    trigger_notification_event(
                        event_type=NotificationEventType.FOLLOWUP_CREATED,
                        recipient=task.assigned_to,
                        context={
                            "user_name": task.assigned_to.get_full_name()
                            or task.assigned_to.username,
                            "employee_name": request.user.get_full_name()
                            or request.user.username,
                            "task_title": task.task_title,
                            "followup_date": str(followup.followup_date),
                        },
                    )
            except Exception:
                logger.exception("Failed to send followup creation notification")

            return Response(
                FollowupSerializer(followup, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while creating FollowUp: user_id=%s",
                request.user.pk,
            )
            return Response(
                {"error": "Something went wrong while creating the FollowUp."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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

    permission_classes = [IsAuthenticated, CanCommunicateWithlead]
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
            followup_id=followup_id,
            is_active=True,
        )

    # ------------------------------------------------------
    # DETAIL
    # ------------------------------------------------------
    @extend_schema(
        tags=["Follow Ups"],
        summary="Retrieve follow-up detail",
        description="GET: Retrieve follow-up detail by ID. Requires view_followup permission.",
        operation_id="followup_retrieve",
        parameters=[
            OpenApiParameter(
                name="followup_id",
                type=int,
                description="Follow-up ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: FollowupSerializer,
            404: inline_serializer(
                "FollowUpDetailNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "FollowUpDetailServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def get(self, request, followup_id):
        try:
            followup = self.get_followup(followup_id)
            self.check_object_permissions(request, followup)
            serializer = FollowupSerializer(followup, context={"request": request})
            logger.info(
                "FollowUp fetched successfully: followup_id=%s user_id=%s",
                followup.followup_id,
                request.user.pk,
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while fetching FollowUp: followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )
            return Response(
                {"error": "Something went wrong while fetching the FollowUp."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------
    @extend_schema(
        tags=["Follow Ups"],
        summary="Partially update a follow-up",
        description="PATCH: Partially update a follow-up. Requires change_followup permission.",
        operation_id="followup_partial_update",
        parameters=[
            OpenApiParameter(
                name="followup_id",
                type=int,
                description="Follow-up ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        request=FollowupSerializer,
        responses={
            200: FollowupSerializer,
            400: FollowupSerializer,
            404: inline_serializer(
                "FollowUpUpdateNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "FollowUpUpdateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def patch(self, request, followup_id):
        try:
            followup = self.get_followup(followup_id)
            self.check_object_permissions(request, followup)
            serializer = FollowupSerializer(
                followup, data=request.data, partial=True, context={"request": request}
            )

            if not serializer.is_valid():
                logger.warning(
                    "FollowUp update validation failed: "
                    "followup_id=%s user_id=%s errors=%s",
                    followup_id,
                    request.user.pk,
                    serializer.errors,
                )
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                followup = serializer.save()

            logger.info(
                "FollowUp updated successfully: followup_id=%s user_id=%s",
                followup.followup_id,
                request.user.pk,
            )

            return Response(
                FollowupSerializer(followup, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while updating FollowUp: followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )
            return Response(
                {"error": "Something went wrong while updating the FollowUp."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------
    # DELETE
    # ------------------------------------------------------
    @extend_schema(
        tags=["Follow Ups"],
        summary="Delete a follow-up",
        description="DELETE: Delete a follow-up. Requires delete_followup permission.",
        operation_id="followup_delete",
        parameters=[
            OpenApiParameter(
                name="followup_id",
                type=int,
                description="Follow-up ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: inline_serializer(
                "FollowUpDeleteSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "followup_id": serializers.IntegerField(),
                },
            ),
            404: inline_serializer(
                "FollowUpDeleteNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "FollowUpDeleteServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def delete(self, request, followup_id):
        try:
            followup = self.get_followup(followup_id)
            self.check_object_permissions(request, followup)

            followup.is_active = False
            followup.save(update_fields=["is_active"])

            logger.info(
                "FollowUp deleted successfully: followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )

            return Response(
                {
                    "message": "FollowUp deleted successfully.",
                    "followup_id": followup_id,
                },
                status=status.HTTP_200_OK,
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while deleting FollowUp: followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )
            return Response(
                {"error": "Something went wrong while deleting the FollowUp."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# FOLLOWUP NOTE
# ==========================================================
class FollowUpNoteCreateView(APIView):
    """
    POST /api/followups/<followup_id>/notes/

    Add a note to a FollowUp.
    """

    permission_classes = [IsAuthenticated, CanCommunicateWithlead]
    permission_names = {
        "POST": "add_followup_note",
    }

    @extend_schema(
        tags=["Follow Ups"],
        summary="Add a note to a follow-up",
        description=(
            "Create a new note associated with a specific follow-up. "
            "The `created_by` field is automatically set to the authenticated user. "
            "Requires the `add_followup_note` permission."
        ),
        operation_id="followup_add_note",
        parameters=[
            OpenApiParameter(
                name="followup_id",
                type=int,
                description="Unique identifier of the parent follow-up",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        request=FollowUpNoteSerializer,
        responses={
            201: FollowUpNoteSerializer,
            400: FollowUpNoteSerializer,
            404: inline_serializer(
                "FollowUpNoteNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "FollowUpNoteServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request, followup_id):
        try:
            followup = get_object_or_404(Followup, followup_id=followup_id)
            self.check_object_permissions(request, followup)
            serializer = FollowUpNoteSerializer(
                data=request.data, context={"request": request}
            )
            if not serializer.is_valid():
                logger.warning(
                    "FollowUp note validation failed: "
                    "followup_id=%s user_id=%s errors=%s",
                    followup_id,
                    request.user.pk,
                    serializer.errors,
                )
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                note = serializer.save(followup_id=followup, created_by=request.user)
            logger.info(
                "FollowUp note created successfully: "
                "note_id=%s followup_id=%s user_id=%s",
                note.note_id,
                followup_id,
                request.user.pk,
            )
            return Response(
                FollowUpNoteSerializer(note, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while creating FollowUp note: followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )
            return Response(
                {"error": "Something went wrong while creating the FollowUp note."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
