import logging
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from .models import FollowUpStatus, Followup
from .serializers import FollowupSerializer, FollowUpStatusUpdateSerializer
from django.db.models import Q
from .pagination import CRMPageNumberPagination
from .permission import CanCommunicateWithlead
from Notification.notification_utils import trigger_notification_event
from Notification.models import NotificationEventType
from audit_log.services import log_audit, log_activity
from audit_log.models import Activity

logger = logging.getLogger(__name__)

from Task.models import Task


# ==========================================================
# FOLLOWUP LIST / CREATE
# ==========================================================
@extend_schema(tags=["Follow Ups"])
class FollowUpListCreateView(APIView):
    """
    GET  /api/followups/   -> List FollowUps (Role-based visibility)
    POST /api/followups/   -> Create FollowUp (Only for assigned task)
    """

    permission_classes = [CanCommunicateWithlead]
    permission_names = {
        "GET": "view_followup",
        "POST": "change_followup",
    }

    # ======================================================
    # 1. LIST FOLLOWUPS
    # ======================================================
    def get(self, request):
        try:
            user = request.user
            followups = Followup.objects.select_related(
                "task_id",
                "task_id__assigned_to",
                "followup_status",
                "followup_type",
                "created_by",
            ).order_by("-created_at")

            if not user.is_superuser:
                role = getattr(user, "role", None)
                if role is None:
                    return Response(
                        {"detail": "No role assigned to user."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                role_name = getattr(role, "rolename", "").strip().lower()

                # Agar Employee hai, toh sirf uske assigned tasks ke follow-ups filter honge
                if role_name not in ["admin", "manager"]:
                    followups = followups.filter(task_id__assigned_to=user)

            # --------------------------------------------------
            # FILTERS
            # --------------------------------------------------
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

            # Only Admin/Manager can filter by another user's created_by
            if created_by_id:
                if user.is_superuser or role_name in ["admin", "manager"]:
                    followups = followups.filter(created_by_id=created_by_id)

            # Search in notes and task_title
            search = request.query_params.get("search")
            if search:
                followups = followups.filter(
                    Q(decription__icontains=search)
                    | Q(task_id__task_title__icontains=search)
                )

            # Ordering
            ordering = request.query_params.get("ordering", "-created_at")
            allowed_ordering_fields = {"created_at", "updated_at", "followup_date"}

            if ordering.lstrip("-") in allowed_ordering_fields:
                followups = followups.order_by(ordering)
            else:
                followups = followups.order_by("-created_at")

            # Pagination
            paginator = CRMPageNumberPagination()
            paginator_followups = paginator.paginate_queryset(
                followups, request, view=self
            )

            serializer = FollowupSerializer(
                paginator_followups, many=True, context={"request": request}
            )

            return paginator.get_paginated_response(serializer.data)

        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while fetching FollowUps: user_id=%s", request.user.pk
            )
            return Response(
                {"error": "Something went wrong while fetching FollowUps."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ======================================================
    # 2. CREATE FOLLOWUP
    # ======================================================
    def post(self, request):
        try:
            task_id = request.data.get("task_id")
            if not task_id:
                return Response(
                    {"task_id": "This field is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            task = get_object_or_404(
                Task.objects.select_related("assigned_to"),
                task_id=task_id,
                is_active=True,
            )

            user = request.user
            role = getattr(user, "role", None)

            if role is None and not user.is_superuser:
                return Response(
                    {"detail": "No role assigned to user."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            role_name = getattr(role, "rolename", "").strip().lower() if role else ""

            if not user.is_superuser and role_name not in ["admin", "manager"]:
                if task.assigned_to_id != user.pk:
                    return Response(
                        {
                            "detail": "You can only create FollowUps for tasks assigned to you."
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

            serializer = FollowupSerializer(
                data=request.data, context={"request": request}
            )

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                followup = serializer.save(created_by=request.user)

            logger.info(
                "FollowUp created successfully: followup_id=%s task_id=%s user_id=%s",
                followup.followup_id,
                task.task_id,
                user.pk,
            )

            log_audit(
                user=request.user,
                entity_type="FollowUp",
                entity_id=followup.followup_id,
                action="FOLLOWUP_CREATED",
                new_value={
                    "task_id": task.task_id,
                    "followup_date": str(followup.followup_date),
                    "followup_status": str(followup.followup_status),
                    "followup_type": str(followup.followup_type),
                },
            )
            log_activity(
                user=request.user,
                activity_type=Activity.ActivityType.FOLLOWUP_CREATED,
                outcome=f"Follow-up created for task: {task.task_title}",
                notes=followup.decription,
                lead=task.lead,
                customer=task.customer,
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
                "Error while creating FollowUp: user_id=%s", request.user.pk
            )
            return Response(
                {"error": "Something went wrong while creating the FollowUp."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# FOLLOWUP DETAIL / UPDATE / DELETE
# ==========================================================
@extend_schema(tags=["Follow Ups"])
class FollowUpDetailView(APIView):
    """
    GET    /api/followups/<followup_id>/ -> Fetch Single FollowUp
    PATCH  /api/followups/<followup_id>/ -> Update FollowUp
    DELETE /api/followups/<followup_id>/ -> Delete FollowUp
    """

    permission_classes = [CanCommunicateWithlead]
    permission_names = {
        "GET": "view_followup",
        "PATCH": "change_followup",
        "DELETE": "delete_followup",
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
            is_active=True,
        )

    def check_followup_access(self, request, followup):
        user = request.user

        # Superuser always allowed
        if user.is_superuser:
            return None

        role = getattr(user, "role", None)
        if role is None:
            return Response(
                {"detail": "No role assigned to user."},
                status=status.HTTP_403_FORBIDDEN,
            )

        role_name = getattr(role, "rolename", "").strip().lower()

        # Admin / Manager allowed for any followup
        if role_name in ["admin", "manager"]:
            return None

        # 🔒 Employee can access ONLY FollowUp of assigned task
        if followup.task_id.assigned_to_id != user.pk:
            logger.warning(
                "FollowUp access denied: followup_id=%s user_id=%s assigned_to=%s",
                followup.followup_id,
                user.pk,
                followup.task_id.assigned_to_id,
            )
            return Response(
                {
                    "detail": "You can only access, update, or delete FollowUps for tasks assigned to you."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return None

    # ======================================================
    # 3. GET SINGLE DETAIL
    # ======================================================
    def get(self, request, followup_id):
        try:
            followup = self.get_followup(followup_id)
            access_error = self.check_followup_access(request, followup)
            if access_error:
                return access_error

            serializer = FollowupSerializer(followup, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while fetching FollowUp: followup_id=%s", followup_id
            )
            return Response(
                {"error": "Something went wrong while fetching the FollowUp."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ======================================================
    # 4. UPDATE (PATCH)
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
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            old_value = {
                "followup_date": str(followup.followup_date),
                "followup_status": str(followup.followup_status),
                "followup_type": str(followup.followup_type),
            }

            with transaction.atomic():
                followup = serializer.save()

            logger.info(
                "FollowUp updated successfully: followup_id=%s user_id=%s",
                followup.followup_id,
                request.user.pk,
            )

            log_audit(
                user=request.user,
                entity_type="FollowUp",
                entity_id=followup.followup_id,
                action="FOLLOWUP_UPDATED",
                old_value=old_value,
                new_value={
                    "followup_date": str(followup.followup_date),
                    "followup_status": str(followup.followup_status),
                    "followup_type": str(followup.followup_type),
                },
            )
            log_activity(
                user=request.user,
                activity_type=Activity.ActivityType.FOLLOWUP_UPDATED,
                outcome=f"Follow-up updated for task: {followup.task_id.task_title}",
                notes=followup.decription,
                lead=followup.task_id.lead,
                customer=followup.task_id.customer,
            )

            try:
                task = followup.task_id
                if task and task.assigned_to and task.assigned_to != request.user:
                    trigger_notification_event(
                        event_type=NotificationEventType.FOLLOWUP_UPDATED,
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
                logger.exception("Failed to send followup update notification")

            return Response(
                FollowupSerializer(followup, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )

        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while updating FollowUp: followup_id=%s", followup_id
            )
            return Response(
                {"error": "Something went wrong while updating the FollowUp."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ======================================================
    # 5. DELETE
    # ======================================================
    def delete(self, request, followup_id):
        try:
            followup = self.get_followup(followup_id)
            access_error = self.check_followup_access(request, followup)
            if access_error:
                return access_error

            task = followup.task_id
            assigned_to = task.assigned_to if task else None
            followup_date = followup.followup_date

            log_audit(
                user=request.user,
                entity_type="FollowUp",
                entity_id=followup.followup_id,
                action="FOLLOWUP_DELETED",
                old_value={
                    "task_id": task.task_id if task else None,
                    "followup_date": str(followup_date),
                    "followup_status": str(followup.followup_status),
                    "followup_type": str(followup.followup_type),
                },
            )
            log_activity(
                user=request.user,
                activity_type=Activity.ActivityType.FOLLOWUP_DELETED,
                outcome=f"Follow-up deleted for task: {task.task_title}",
                lead=task.lead,
                customer=task.customer,
            )

            followup.delete()

            logger.info(
                "FollowUp deleted successfully: followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )

            try:
                if task and assigned_to and assigned_to != request.user:
                    trigger_notification_event(
                        event_type=NotificationEventType.FOLLOWUP_DELETED,
                        recipient=assigned_to,
                        context={
                            "user_name": assigned_to.get_full_name()
                            or assigned_to.username,
                            "employee_name": request.user.get_full_name()
                            or request.user.username,
                            "task_title": task.task_title,
                            "followup_date": str(followup_date),
                        },
                    )
            except Exception:
                logger.exception("Failed to send followup deletion notification")

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
                "Error while deleting FollowUp: followup_id=%s", followup_id
            )
            return Response(
                {"error": "Something went wrong while deleting the FollowUp."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(tags=["Follow Ups"])
class FollowUpStatusUpdateView(APIView):
    """
    PATCH /api/followups/<followup_id>/status/

    Assigned employee, Manager, Admin and Superuser
    can update FollowUp status.
    """

    permission_classes = [CanCommunicateWithlead]

    permission_names = {
        "PATCH": "change_followupstatus",
    }

    def patch(self, request, followup_id):
        try:
            # ----------------------------------------------
            # GET FOLLOWUP
            # ----------------------------------------------

            followup = get_object_or_404(
                Followup.objects.select_related(
                    "task_id",
                    "task_id__assigned_to",
                    "followup_status",
                ),
                followup_id=followup_id,
                is_active=True,
            )

            user = request.user

            # ----------------------------------------------
            # SUPERUSER
            # ----------------------------------------------

            if user.is_superuser:
                allowed = True

            else:
                role = getattr(user, "role", None)

                if role is None:
                    return Response(
                        {"detail": "No role assigned to user."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                role_name = getattr(role, "rolename", "").strip().lower()

                # ------------------------------------------
                # ADMIN / MANAGER
                # ------------------------------------------

                if role_name in ["admin", "manager"]:
                    allowed = True

                # ------------------------------------------
                # EMPLOYEE
                # Only assigned employee
                # ------------------------------------------

                else:
                    if followup.task_id.assigned_to_id == user.pk:
                        allowed = True
                    else:
                        allowed = False

            # ----------------------------------------------
            # ACCESS DENIED
            # ----------------------------------------------

            if not allowed:
                return Response(
                    {
                        "detail": (
                            "You can only update the status of "
                            "FollowUps assigned to you."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # ----------------------------------------------
            # VALIDATE REQUEST
            # ----------------------------------------------

            serializer = FollowUpStatusUpdateSerializer(data=request.data)

            serializer.is_valid(raise_exception=True)

            status_id = serializer.validated_data["status_id"]

            # ----------------------------------------------
            # GET NEW STATUS
            # ----------------------------------------------

            new_status = get_object_or_404(
                FollowUpStatus,
                followup_status_id=status_id,
                is_active=True,
            )

            old_status = followup.followup_status

            # ----------------------------------------------
            # UPDATE
            # ----------------------------------------------

            with transaction.atomic():

                followup.followup_status = new_status

                followup.save(
                    update_fields=[
                        "followup_status",
                    ]
                )

            # ----------------------------------------------
            # LOG
            # ----------------------------------------------

            logger.info(
                "FollowUp status updated successfully: "
                "followup_id=%s old_status=%s "
                "new_status=%s user_id=%s",
                followup.followup_id,
                old_status.status_name if old_status else None,
                new_status.status_name,
                user.pk,
            )

            # ----------------------------------------------
            # RESPONSE
            # ----------------------------------------------

            return Response(
                {
                    "message": ("FollowUp status updated successfully."),
                    "followup_id": followup.followup_id,
                    "previous_status": (old_status.status_name if old_status else None),
                    "new_status": new_status.status_name,
                },
                status=status.HTTP_200_OK,
            )

        except (Http404, APIException):
            raise

        except Exception:
            logger.exception(
                "Error while updating FollowUp status: " "followup_id=%s user_id=%s",
                followup_id,
                request.user.pk,
            )

            return Response(
                {"error": ("Something went wrong while " "updating FollowUp status.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
