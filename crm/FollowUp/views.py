import logging
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import (
    Followup,
    FollowUpNote,
)
from .serializers import (
    FollowupSerializer,
    FollowUpNoteSerializer,
)
from django.db.models import Q
from .pagination import CRMPageNumberPagination
from .permission import CanCommunicateWithlead

logger = logging.getLogger(__name__)

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
    permission_classes = [CanCommunicateWithlead]
    permission_names = {
                    "POST": "add_followup",
    }
    # ------------------------------------------------------
    # LIST FOLLOWUPS
    # ------------------------------------------------------
    def get(self, request):
        try:
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
            # filter =========================================
            followup_status_id = request.query_params.get("followup_status")
            followup_type_id = request.query_params.get("followup_type")
            task_id = request.query_params.get("task_id")
            created_by_id = request.query_params.get("created_by")
            if followup_status_id:
                followups = followups.filter(
                    followup_status_id=followup_status_id
                )
            if followup_type_id:
                followups = followups.filter(
                    followup_type_id=followup_type_id
                )
            if task_id:
                followups = followups.filter(
                    task_id=task_id
                )
            if created_by_id:
                followups = followups.filter(
                    created_by_id=created_by_id
                )
            # search ==============================
            search = request.query_params.get("search")
            if search:
                followups = followups.filter(
                    Q(decription__icontains=search)
                    | Q(task_id__task_title__icontains=search)
                )
            # dynamic ordering =============================
            ordering = request.query_params.get(
                "ordering",
                "-created_at"
            )
            allowed_ordering_fields = {
                "created_at",
                "updated_at"
            }
            if ordering.lstrip("-") in allowed_ordering_fields:
                followups = followups.order_by(ordering)
            else:
                followups = followups.order_by("-created_at")
            # pagination =========================================
            paginator = CRMPageNumberPagination()
            paginator_followups = paginator.paginate_queryset(followups, request, view=self)
            serializer = FollowupSerializer(
                paginator_followups,
                many=True,
                context={"request": request}
            )
            logger.info(
                "FollowUps fetched successfully: user_id=%s page=%s",
                request.user.pk,
                request.query_params.get("page", 1)
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
                {
                    "error": "Something went wrong while fetching FollowUps."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ------------------------------------------------------
    # CREATE FOLLOWUP
    # ------------------------------------------------------
    def post(self, request):
        
        try:
            serializer = FollowupSerializer(
                data=request.data,
                context={"request": request}
            )
            if not serializer.is_valid():
                logger.warning(
                    "FollowUp creation validation failed: "
                    "user_id=%s errors=%s",
                    request.user.pk,
                    serializer.errors,
                )
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )
            followup = serializer.save(
                created_by=request.user
            )
            logger.info(
                "FollowUp created successfully: "
                "followup_id=%s user_id=%s",
                followup.followup_id,
                request.user.pk,
            )
            return Response(
                FollowupSerializer(
                    followup,
                    context={"request": request}
                ).data,
                status=status.HTTP_201_CREATED
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while creating FollowUp: user_id=%s",
                request.user.pk,
            )
            return Response(
                {
                    "error": "Something went wrong while creating the FollowUp."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
        try:
            followup = self.get_followup(followup_id)
            self.check_object_permissions(
                request,
                followup
            )
            serializer = FollowupSerializer(
                followup,
                context={"request": request}
            )
            logger.info(
                "FollowUp fetched successfully: "
                "followup_id=%s user_id=%s",
                followup.followup_id,
                request.user.pk,
            )
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while fetching FollowUp: "
                "followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )
            return Response(
                {
                    "error": "Something went wrong while fetching the FollowUp."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------
    def patch(self, request, followup_id):
        try:
            followup = self.get_followup(followup_id)
            self.check_object_permissions(
                request,
                followup
            )
            serializer = FollowupSerializer(
                followup,
                data=request.data,
                partial=True,
                context={"request": request}
            )

            if not serializer.is_valid():
                logger.warning(
                    "FollowUp update validation failed: "
                    "followup_id=%s user_id=%s errors=%s",
                    followup_id,
                    request.user.pk,
                    serializer.errors,
                )
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

            followup = serializer.save()

            logger.info(
                "FollowUp updated successfully: "
                "followup_id=%s user_id=%s",
                followup.followup_id,
                request.user.pk,
            )

            return Response(
                FollowupSerializer(
                    followup,
                    context={"request": request}
                ).data,
                status=status.HTTP_200_OK
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while updating FollowUp: "
                "followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )
            return Response(
                {
                    "error": "Something went wrong while updating the FollowUp."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ------------------------------------------------------
    # DELETE
    # ------------------------------------------------------
    def delete(self, request, followup_id):
        try:
            followup = self.get_followup(followup_id)
            self.check_object_permissions(
                request,
                followup
            )
            followup.delete()

            logger.info(
                "FollowUp deleted successfully: "
                "followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )

            return Response(
                {
                    "message": "FollowUp deleted successfully.",
                    "followup_id": followup_id
                },
                status=status.HTTP_200_OK
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while deleting FollowUp: "
                "followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )
            return Response(
                {
                    "error": "Something went wrong while deleting the FollowUp."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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

    def post(self, request, followup_id):
        try:
            followup = get_object_or_404(
                Followup,
                followup_id=followup_id
            )
            self.check_object_permissions(
                request,
                followup
            )
            serializer = FollowUpNoteSerializer(
                data=request.data,
                context={"request": request}
            )
            if not serializer.is_valid():
                logger.warning(
                    "FollowUp note validation failed: "
                    "followup_id=%s user_id=%s errors=%s",
                    followup_id,
                    request.user.pk,
                    serializer.errors,
                )
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )
            note = serializer.save(
                followup_id=followup,
                created_by=request.user
            )
            logger.info(
                "FollowUp note created successfully: "
                "note_id=%s followup_id=%s user_id=%s",
                note.note_id,
                followup_id,
                request.user.pk,
            )
            return Response(
                FollowUpNoteSerializer(
                    note,
                    context={"request": request}
                ).data,
                status=status.HTTP_201_CREATED
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while creating FollowUp note: "
                "followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )
            return Response(
                {
                    "error": "Something went wrong while creating the FollowUp note."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


