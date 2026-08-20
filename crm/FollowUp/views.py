import logging
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status, serializers
from rest_framework.exceptions import APIException
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

logger = logging.getLogger(__name__)

from Task.models import Task


# ==========================================================
# FOLLOWUP LIST / CREATE
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

    # ======================================================
    # LIST FOLLOWUPS
    # ======================================================

    def get(self, request):

        try:

            followups = Followup.objects.select_related(
                "task_id",
                "task_id__assigned_to",
                "followup_status",
                "followup_type",
                "created_by",
            ).order_by("-created_at")

            # ==================================================
            # FILTERS
            # ==================================================

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

            # ==================================================
            # SEARCH
            # ==================================================

            search = request.query_params.get("search")

            if search:
                followups = followups.filter(
                    Q(description__icontains=search)
                    | Q(task_id__task_title__icontains=search)
                )

            # ==================================================
            # ORDERING
            # ==================================================

            ordering = request.query_params.get("ordering", "-created_at")

            allowed_ordering_fields = {
                "created_at",
                "updated_at",
            }

            if ordering.lstrip("-") in allowed_ordering_fields:
                followups = followups.order_by(ordering)
            else:
                followups = followups.order_by("-created_at")

            # ==================================================
            # PAGINATION
            # ==================================================

            paginator = CRMPageNumberPagination()

            paginator_followups = paginator.paginate_queryset(
                followups, request, view=self
            )

            serializer = FollowupSerializer(
                paginator_followups, many=True, context={"request": request}
            )

            logger.info(
                "FollowUps fetched successfully: " "user_id=%s page=%s",
                request.user.pk,
                request.query_params.get("page", 1),
            )

            return paginator.get_paginated_response(serializer.data)

        except (Http404, APIException):
            raise

        except Exception:

            logger.exception(
                "Error while fetching FollowUps: " "user_id=%s",
                request.user.pk,
            )

            return Response(
                {"error": ("Something went wrong while " "fetching FollowUps.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ======================================================
    # CREATE FOLLOWUP
    # ======================================================

    def post(self, request):

        try:

            # ----------------------------------------------
            # GET TASK ID FROM REQUEST
            # ----------------------------------------------

            task_id = request.data.get("task_id")

            if not task_id:

                logger.warning(
                    "FollowUp creation failed: " "task_id missing user_id=%s",
                    request.user.pk,
                )

                return Response(
                    {"task_id": ("This field is required.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ----------------------------------------------
            # GET TASK
            # ----------------------------------------------

            task = get_object_or_404(
                Task.objects.select_related("assigned_to"),
                task_id=task_id,
                is_active=True,
            )

            user = request.user

            # ----------------------------------------------
            # GET ROLE
            # ----------------------------------------------

            role = getattr(user, "role", None)

            if role is None:

                logger.warning(
                    "FollowUp creation denied: " "no role assigned user_id=%s",
                    user.pk,
                )

                return Response(
                    {"detail": ("No role assigned to user.")},
                    status=status.HTTP_403_FORBIDDEN,
                )

            role_name = getattr(role, "rolename", "").strip().lower()

            # ==================================================
            # ADMIN / MANAGER
            # Can create FollowUp for any task
            # ==================================================

            if user.is_superuser or role_name in [
                "admin",
                "manager",
            ]:

                logger.info(
                    "FollowUp creation authorized for "
                    "Admin/Manager: user_id=%s "
                    "task_id=%s",
                    user.pk,
                    task.task_id,
                )

            # ==================================================
            # EMPLOYEE
            # Can create FollowUp ONLY for assigned task
            # ==================================================

            else:

                if task.assigned_to_id != user.pk:

                    logger.warning(
                        "FollowUp creation denied: "
                        "user_id=%s task_id=%s "
                        "assigned_to_id=%s",
                        user.pk,
                        task.task_id,
                        task.assigned_to_id,
                    )

                    return Response(
                        {
                            "detail": (
                                "You can only create "
                                "FollowUps for tasks "
                                "assigned to you."
                            )
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

                logger.info(
                    "FollowUp creation authorized for "
                    "assigned employee: user_id=%s "
                    "task_id=%s",
                    user.pk,
                    task.task_id,
                )

            # ==================================================
            # SERIALIZER VALIDATION
            # ==================================================

            serializer = FollowupSerializer(
                data=request.data, context={"request": request}
            )

            if not serializer.is_valid():

                logger.warning(
                    "FollowUp creation validation failed: "
                    "user_id=%s task_id=%s errors=%s",
                    user.pk,
                    task.task_id,
                    serializer.errors,
                )

                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # ==================================================
            # SAVE FOLLOWUP
            # ==================================================

            followup = serializer.save(created_by=user)

            logger.info(
                "FollowUp created successfully: "
                "followup_id=%s task_id=%s user_id=%s",
                followup.followup_id,
                task.task_id,
                user.pk,
            )

            return Response(
                FollowupSerializer(followup, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        except (Http404, APIException):
            raise

        except Exception:

            logger.exception(
                "Error while creating FollowUp: " "user_id=%s",
                request.user.pk,
            )

            return Response(
                {"error": ("Something went wrong while " "creating the FollowUp.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# FOLLOWUP DETAIL / UPDATE / DELETE
# ==========================================================
class FollowUpDetailView(APIView):
    """
    GET    /api/followups/<followup_id>/
        Admin/Manager -> any FollowUp
        Assigned Employee -> only FollowUp of assigned task

    PATCH  /api/followups/<followup_id>/
        Admin/Manager -> any FollowUp
        Assigned Employee -> only FollowUp of assigned task

    DELETE /api/followups/<followup_id>/
        Admin/Manager -> any FollowUp
        Assigned Employee -> only FollowUp of assigned task
    """

    permission_classes = [CanCommunicateWithlead]

    permission_names = {
        "PATCH": "change_followupnote",
        "GET": "view_followupnote",
        "DELETE": "delete_followupnote",
    }

    def get_followup(self, followup_id):
        return get_object_or_404(
            Followup.objects.select_related(
                "task_id",
                "task_id__assigned_to",
                "followup_status",
                "followup_type",
                "created_by",
            ),
            followup_id=followup_id,
        )

    # ======================================================
    # CHECK FOLLOWUP ACCESS
    # ======================================================

    def check_followup_access(self, request, followup):
        user = request.user

        # Superuser can access everything
        if user.is_superuser:
            return None

        role = getattr(user, "role", None)

        if role is None:
            logger.warning(
                "FollowUp access denied: " "no role assigned user_id=%s", user.pk
            )

            return Response(
                {"detail": "No role assigned to user."},
                status=status.HTTP_403_FORBIDDEN,
            )

        role_name = getattr(role, "rolename", "").strip().lower()

        # Admin / Manager can access any FollowUp
        if role_name in ["admin", "manager"]:
            return None

        # Employee can access ONLY FollowUp of assigned task
        if followup.task_id.assigned_to_id != user.pk:

            logger.warning(
                "FollowUp access denied: "
                "followup_id=%s user_id=%s "
                "assigned_to_id=%s",
                followup.followup_id,
                user.pk,
                followup.task_id.assigned_to_id,
            )

            return Response(
                {
                    "detail": (
                        "You can only access FollowUps " "for tasks assigned to you."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return None

    # ======================================================
    # DETAIL
    # ======================================================

    def get(self, request, followup_id):
        try:
            followup = self.get_followup(followup_id)

            access_error = self.check_followup_access(request, followup)

            if access_error:
                return access_error

            serializer = FollowupSerializer(followup, context={"request": request})

            logger.info(
                "FollowUp fetched successfully: " "followup_id=%s user_id=%s",
                followup.followup_id,
                request.user.pk,
            )

            return Response(serializer.data, status=status.HTTP_200_OK)

        except (Http404, APIException):
            raise

        except Exception:
            logger.exception(
                "Error while fetching FollowUp: " "followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )

            return Response(
                {"error": ("Something went wrong while " "fetching the FollowUp.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ======================================================
    # UPDATE
    # ======================================================

    def patch(self, request, followup_id):
        try:
            followup = self.get_followup(followup_id)

            access_error = self.check_followup_access(request, followup)

            if access_error:
                return access_error

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

            followup = serializer.save()

            logger.info(
                "FollowUp updated successfully: " "followup_id=%s user_id=%s",
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
                "Error while updating FollowUp: " "followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )

            return Response(
                {"error": ("Something went wrong while " "updating the FollowUp.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ======================================================
    # DELETE
    # ======================================================

    def delete(self, request, followup_id):
        try:
            followup = self.get_followup(followup_id)

            access_error = self.check_followup_access(request, followup)

            if access_error:
                return access_error

            followup.delete()

            logger.info(
                "FollowUp deleted successfully: " "followup_id=%s user_id=%s",
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
                "Error while deleting FollowUp: " "followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )

            return Response(
                {"error": ("Something went wrong while " "deleting the FollowUp.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# FOLLOWUP NOTE
# ==========================================================
class FollowUpNoteCreateView(APIView):

    permission_classes = [CanCommunicateWithlead]

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

            followup = get_object_or_404(
                Followup.objects.select_related(
                    "task_id",
                    "task_id__assigned_to",
                ),
                followup_id=followup_id,
            )

            user = request.user

            # ==================================================
            # CHECK WHO CAN ADD NOTE
            # ==================================================

            if not user.is_superuser:

                role = getattr(user, "role", None)

                if role is None:
                    return Response(
                        {"detail": "No role assigned to user."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                role_name = getattr(role, "rolename", "").strip().lower()

                # Admin / Manager -> any FollowUp note
                if role_name in ["admin", "manager"]:
                    pass

                # Employee -> only FollowUp of assigned task
                else:

                    if followup.task_id.assigned_to_id != user.pk:

                        logger.warning(
                            "FollowUp note creation denied: "
                            "followup_id=%s user_id=%s "
                            "assigned_to_id=%s",
                            followup_id,
                            user.pk,
                            followup.task_id.assigned_to_id,
                        )

                        return Response(
                            {
                                "detail": (
                                    "You can only add notes "
                                    "to FollowUps for tasks "
                                    "assigned to you."
                                )
                            },
                            status=status.HTTP_403_FORBIDDEN,
                        )

            # ==================================================
            # SERIALIZER
            # ==================================================

            serializer = FollowUpNoteSerializer(
                data=request.data, context={"request": request}
            )

            if not serializer.is_valid():

                logger.warning(
                    "FollowUp note validation failed: "
                    "followup_id=%s user_id=%s errors=%s",
                    followup_id,
                    user.pk,
                    serializer.errors,
                )

                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # ==================================================
            # CREATE NOTE
            # ==================================================

            note = serializer.save(followup_id=followup, created_by=user)

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
