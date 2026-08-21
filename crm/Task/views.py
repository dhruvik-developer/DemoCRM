from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db import transaction
import logging

from rest_framework import status, serializers
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Q

from .permission import HasDynamicPermission, CanCommunicateWithLead

from .models import (
    Task,
    TaskStatus,
    Meeting,
    MeetingStatus,
    MeetingParticipant,
    Reminder,
    ReminderStatus,
)

from .serializers import (
    TaskSerializer,
    MeetingSerializer,
    MeetingParticipantSerializer,
    ReminderSerializer,
)

from .pagination import CRMPageNumberPagination
from .services import send_meeting_creation_emails
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer

from Notification.notification_utils import trigger_notification_event
from Notification.models import NotificationEventType

logger = logging.getLogger(__name__)

User = get_user_model()


# ==========================================================
# TASK LIST / CREATE
# ==========================================================


class TaskListCreateView(APIView):
    """
    GET  /api/tasks/
        Admin/Manager -> all tasks
        Employee       -> only assigned tasks

    POST /api/tasks/
        Only Admin/Manager can create task
    """

    def get_permissions(self):
        """
        GET:
            Any authenticated user can access the list,
            but queryset will be restricted to assigned tasks.

        POST:
            HasDynamicPermission checks task_create.
        """

        if self.request.method == "POST":
            return [
                IsAuthenticated(),
                HasDynamicPermission(),
            ]

        return [
            IsAuthenticated(),
        ]

    permission_classes = [CanCommunicateWithLead]
    permission_names = {
        "POST": "add_task",
    }

    @extend_schema(
        tags=["Tasks"],
        summary="List tasks",
        description="GET: List tasks. Admin/Manager see all tasks, Employee sees only assigned tasks. Auth: IsAuthenticated.",
        operation_id="task_list",
        parameters=[
            OpenApiParameter(
                name="status",
                type=int,
                description="Filter by task status ID",
                required=False,
            ),
            OpenApiParameter(
                name="priority",
                type=int,
                description="Filter by priority ID",
                required=False,
            ),
            OpenApiParameter(
                name="category",
                type=int,
                description="Filter by category ID",
                required=False,
            ),
            OpenApiParameter(
                name="assigned_to",
                type=int,
                description="Filter by assigned user ID (Admin/Manager only)",
                required=False,
            ),
            OpenApiParameter(
                name="lead", type=int, description="Filter by lead ID", required=False
            ),
            OpenApiParameter(
                name="customer",
                type=int,
                description="Filter by customer ID",
                required=False,
            ),
            OpenApiParameter(
                name="search",
                type=str,
                description="Search in task title and description",
                required=False,
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                description="Order by field (due_date, created_at, updated_at, status, priority, task_title). Prefix with - for descending.",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=int,
                description="Page number for pagination",
                required=False,
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                description="Number of results per page",
                required=False,
            ),
        ],
        responses={
            200: TaskSerializer(many=True),
            400: inline_serializer(
                "TaskListErrorResponse", fields={"error": serializers.CharField()}
            ),
            403: inline_serializer(
                "TaskListForbiddenResponse", fields={"detail": serializers.CharField()}
            ),
            500: inline_serializer(
                "TaskListServerErrorResponse", fields={"error": serializers.CharField()}
            ),
        },
    )
    def get(self, request):
        try:
            tasks = (
                Task.objects.filter(is_active=True)
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

            # ==================================================
            # ROLE BASED TASK VISIBILITY
            # ==================================================

            user = request.user

            if not user.is_superuser:
                role = getattr(user, "role", None)

                if role is None:
                    return Response(
                        {"detail": "No role assigned to this user."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                role_name = getattr(role, "rolename", "").strip().lower()

                # Employee / other users:
                # only their assigned tasks
                if role_name not in ["admin", "manager"]:
                    tasks = tasks.filter(assigned_to=user)

            # ==================================================
            # FILTERS
            # ==================================================

            status_id = request.query_params.get("status")
            priority_id = request.query_params.get("priority")
            category_id = request.query_params.get("category")
            assigned_to_id = request.query_params.get("assigned_to")
            lead_id = request.query_params.get("lead")
            customer_id = request.query_params.get("customer")

            if status_id:
                tasks = tasks.filter(status_id=status_id)

            if priority_id:
                tasks = tasks.filter(priority_id=priority_id)

            if category_id:
                tasks = tasks.filter(category_id=category_id)

            # Only Admin/Manager should be able to
            # intentionally filter another user's tasks.
            if assigned_to_id:
                if user.is_superuser or (
                    getattr(user, "role", None)
                    and getattr(user.role, "rolename", "").strip().lower()
                    in ["admin", "manager"]
                ):
                    tasks = tasks.filter(assigned_to_id=assigned_to_id)

            if lead_id:
                tasks = tasks.filter(lead_id=lead_id)

            if customer_id:
                tasks = tasks.filter(customer_id=customer_id)

            # ==================================================
            # SEARCH
            # ==================================================

            search = request.query_params.get("search")

            if search:
                tasks = tasks.filter(
                    Q(task_title__icontains=search) | Q(description__icontains=search)
                )

            # ==================================================
            # ORDERING
            # ==================================================

            ordering = request.query_params.get("ordering", "-created_at")

            allowed_ordering_fields = {
                "due_date",
                "created_at",
                "updated_at",
                "status",
                "priority",
                "task_title",
            }

            if ordering.lstrip("-") in allowed_ordering_fields:
                tasks = tasks.order_by(ordering)
            else:
                tasks = tasks.order_by("-created_at")

            # ==================================================
            # PAGINATION
            # ==================================================

            paginator = CRMPageNumberPagination()

            paginated_task = paginator.paginate_queryset(tasks, request, view=self)

            serializer = TaskSerializer(
                paginated_task, many=True, context={"request": request}
            )

            logger.info("Tasks fetched successfully: user_id=%s", request.user.pk)

            return paginator.get_paginated_response(serializer.data)

        except (Http404, APIException):
            raise

        except Exception:
            logger.exception("Error while fetching tasks: user_id=%s", request.user.pk)

            return Response(
                {"error": ("Something went wrong while fetching tasks.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        tags=["Tasks"],
        summary="Create a task",
        description="POST: Create a new task. Permission: add_task.",
        operation_id="task_create",
        request=TaskSerializer,
        responses={
            201: TaskSerializer,
            400: TaskSerializer,
            403: inline_serializer(
                "TaskCreateForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "TaskCreateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        try:
            serializer = TaskSerializer(data=request.data, context={"request": request})

            if not serializer.is_valid():
                logger.warning(
                    "Task validation failed: user_id=%s errors=%s",
                    request.user.pk,
                    serializer.errors,
                )

                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                task = serializer.save(created_by=request.user)

            logger.info(
                "Task created successfully: task_id=%s user_id=%s",
                task.task_id,
                request.user.pk,
            )

            if task.assigned_to and task.assigned_to != request.user:
                trigger_notification_event(
                    event_type=NotificationEventType.TASK_ASSIGNED,
                    recipient=task.assigned_to,
                    context={
                        "user_name": task.assigned_to.get_full_name()
                        or task.assigned_to.username,
                        "employee_name": request.user.get_full_name()
                        or request.user.username,
                        "task_title": task.task_title,
                        "due_date": str(task.due_date) if task.due_date else "N/A",
                    },
                )

            return Response(
                TaskSerializer(task, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        except (Http404, APIException):
            raise

        except Exception:
            logger.exception("Error while creating task: user_id=%s", request.user.pk)

            return Response(
                {"error": ("Something went wrong while creating the task.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# TASK DETAIL / UPDATE / DELETE
# ==========================================================


class TaskDetailView(APIView):
    def get_permissions(self):
        # ---------------------------------------------
        # GET
        # Employee can view assigned task
        # Admin/Manager can view any task
        # ---------------------------------------------
        if self.request.method == "GET":
            return [
                IsAuthenticated(),
            ]

        # ---------------------------------------------
        # PATCH
        # Employee can update assigned task
        # Admin/Manager can update any task
        # ---------------------------------------------
        if self.request.method == "PATCH":
            return [
                IsAuthenticated(),
            ]

        if self.request.method == "DELETE":
            return [
                IsAuthenticated(),
            ]
        # ---------------------------------------------
        # DELETE
        # Only dynamic permission
        # ---------------------------------------------
        return [
            IsAuthenticated(),
            HasDynamicPermission(),
        ]

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
            is_active=True,
        )

    # ======================================================
    # GET TASK DETAIL
    # ======================================================

    @extend_schema(
        tags=["Tasks"],
        summary="Retrieve task detail",
        description="Retrieve details of a task by ID. Auth: IsAuthenticated.",
        operation_id="task_retrieve",
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=int,
                description="Task ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: TaskSerializer,
            403: inline_serializer(
                "TaskDetailForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "TaskDetailNotFoundResponse", fields={"detail": serializers.CharField()}
            ),
            500: inline_serializer(
                "TaskDetailServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def get(self, request, task_id):
        try:
            task = self.get_task(task_id)
            user = request.user

            # ---------------------------------------------
            # ADMIN / SUPERUSER
            # Can see any task
            # ---------------------------------------------
            if user.is_superuser:
                pass

            else:
                role = getattr(user, "role", None)

                if role is None:
                    return Response(
                        {"detail": ("No role assigned to this user.")},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                role_name = getattr(role, "rolename", "").strip().lower()

                # -----------------------------------------
                # ADMIN / MANAGER
                # Can see any task
                # -----------------------------------------
                if role_name in ["admin", "manager"]:
                    pass

                # -----------------------------------------
                # EMPLOYEE
                # Only assigned task
                # -----------------------------------------
                else:
                    if task.assigned_to_id != user.pk:
                        return Response(
                            {"detail": ("You can only view tasks assigned to you.")},
                            status=status.HTTP_403_FORBIDDEN,
                        )

            serializer = TaskSerializer(task, context={"request": request})

            return Response(serializer.data, status=status.HTTP_200_OK)

        except (Http404, APIException):
            raise

        except Exception:
            logger.exception(
                "Error while fetching task: task_id=%s user_id=%s",
                task_id,
                request.user.pk,
            )

            return Response(
                {"error": ("Something went wrong while fetching the task.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ======================================================
    # UPDATE TASK
    # ======================================================

    @extend_schema(
        tags=["Tasks"],
        summary="Partially update a task",
        description="Partially update a task. Auth: IsAuthenticated.",
        operation_id="task_partial_update",
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=int,
                description="Task ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        request=TaskSerializer,
        responses={
            200: TaskSerializer,
            400: TaskSerializer,
            403: inline_serializer(
                "TaskUpdateForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "TaskUpdateNotFoundResponse", fields={"detail": serializers.CharField()}
            ),
            500: inline_serializer(
                "TaskUpdateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def patch(self, request, task_id):
        try:
            task = self.get_task(task_id)
            user = request.user

            # ---------------------------------------------
            # CHECK WHO CAN UPDATE
            # ---------------------------------------------

            if not user.is_superuser:
                role = getattr(user, "role", None)

                if role is None:
                    return Response(
                        {"detail": ("No role assigned to user.")},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                role_name = getattr(role, "rolename", "").strip().lower()

                # -----------------------------------------
                # ADMIN / MANAGER
                # Can update any task
                # -----------------------------------------
                if role_name in ["admin", "manager"]:
                    pass

                # -----------------------------------------
                # EMPLOYEE
                # Only assigned task
                # -----------------------------------------
                else:
                    if task.assigned_to_id != user.pk:
                        return Response(
                            {"detail": ("You can only update tasks assigned to you.")},
                            status=status.HTTP_403_FORBIDDEN,
                        )

            # ---------------------------------------------
            # SERIALIZER
            # ---------------------------------------------

            serializer = TaskSerializer(
                task, data=request.data, partial=True, context={"request": request}
            )

            if not serializer.is_valid():
                logger.warning(
                    "Task update validation failed: task_id=%s user_id=%s errors=%s",
                    task_id,
                    request.user.pk,
                    serializer.errors,
                )

                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                task = serializer.save()

            logger.info(
                "Task updated successfully: task_id=%s user_id=%s",
                task.task_id,
                request.user.pk,
            )

            if task.assigned_to and task.assigned_to != request.user:
                trigger_notification_event(
                    event_type=NotificationEventType.TASK_UPDATED,
                    recipient=task.assigned_to,
                    context={
                        "user_name": task.assigned_to.get_full_name()
                        or task.assigned_to.username,
                        "employee_name": request.user.get_full_name()
                        or request.user.username,
                        "task_title": task.task_title,
                        "due_date": str(task.due_date) if task.due_date else "N/A",
                    },
                )

            return Response(
                TaskSerializer(task, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )

        except (Http404, APIException):
            raise

        except Exception:
            logger.exception(
                "Error while updating task: task_id=%s user_id=%s",
                task_id,
                request.user.pk,
            )

            return Response(
                {"error": ("Something went wrong while updating the task.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ======================================================
    # DELETE TASK
    # ======================================================

    @extend_schema(
        tags=["Tasks"],
        summary="Delete a task",
        description="Soft-delete a task (sets is_active=False). Auth: IsAuthenticated.",
        operation_id="task_delete",
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=int,
                description="Task ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: inline_serializer(
                "TaskDeleteSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "task_id": serializers.IntegerField(),
                },
            ),
            403: inline_serializer(
                "TaskDeleteForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "TaskDeleteNotFoundResponse", fields={"detail": serializers.CharField()}
            ),
            500: inline_serializer(
                "TaskDeleteServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def delete(self, request, task_id):
        try:
            task = self.get_task(task_id)
            user = request.user

            # ==================================================
            # CHECK WHO CAN DELETE
            # ==================================================

            if not user.is_superuser:
                role = getattr(user, "role", None)

                if role is None:
                    return Response(
                        {"detail": "No role assigned to user."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                role_name = getattr(role, "rolename", "").strip().lower()

                # ----------------------------------------------
                # ADMIN / MANAGER
                # Can delete any task
                # ----------------------------------------------
                if role_name in ["admin", "manager"]:
                    pass
                # ----------------------------------------------
                # EMPLOYEE
                # Can delete only assigned task
                # ----------------------------------------------
                else:
                    if task.assigned_to_id != user.pk:
                        return Response(
                            {"detail": ("You can only delete tasks assigned to you.")},
                            status=status.HTTP_403_FORBIDDEN,
                        )

            # ==================================================
            # SOFT DELETE
            # ==================================================

            task.is_active = False

            task.save(update_fields=["is_active"])

            logger.info(
                "Task soft deleted successfully: task_id=%s user_id=%s",
                task.task_id,
                request.user.pk,
            )

            return Response(
                {"message": "Task deleted successfully.", "task_id": task.task_id},
                status=status.HTTP_200_OK,
            )

        except (Http404, APIException):
            raise

        except Exception:
            logger.exception(
                "Error while deleting task: task_id=%s user_id=%s",
                task_id,
                request.user.pk,
            )

            return Response(
                {"error": ("Something went wrong while deleting the task.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# ASSIGN TASK
# ==========================================================


class TaskAssignView(APIView):
    """
    POST /api/tasks/<task_id>/assign/

    Only Admin/Manager with task_assign permission
    can assign or reassign a task.
    """

    permission_classes = [
        IsAuthenticated,
        HasDynamicPermission,
    ]

    permission_names = {
        "POST": "task_assign",
    }

    @extend_schema(
        tags=["Tasks"],
        summary="Assign or reassign a task",
        description="Assign or reassign a task to a user. Only users with task_assign permission (Admin/Manager) can perform this action.",
        operation_id="task_assign",
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=int,
                description="Task ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "assigned_to": {
                        "type": "integer",
                        "description": "User ID to assign the task to",
                    },
                },
                "required": ["assigned_to"],
            }
        },
        responses={
            200: inline_serializer(
                "TaskAssignSuccessResponse",
                fields={"message": serializers.CharField(), "task": TaskSerializer()},
            ),
            400: inline_serializer(
                "TaskAssignErrorResponse",
                fields={"assigned_to": serializers.CharField()},
            ),
            404: inline_serializer(
                "TaskAssignNotFoundResponse", fields={"detail": serializers.CharField()}
            ),
            500: inline_serializer(
                "TaskAssignServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request, task_id):
        try:
            task = get_object_or_404(Task, task_id=task_id, is_active=True)

            assigned_to_id = request.data.get("assigned_to")

            if not assigned_to_id:
                logger.warning(
                    "Task assignment failed: assigned_to missing task_id=%s user_id=%s",
                    task_id,
                    request.user.pk,
                )

                return Response(
                    {"assigned_to": ("This field is required.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_user = get_object_or_404(User, pk=assigned_to_id)

            old_user = task.assigned_to

            with transaction.atomic():
                task.assigned_to = new_user

                task.save(
                    update_fields=[
                        "assigned_to",
                        "updated_at",
                    ]
                )

            event_type = (
                NotificationEventType.TASK_REASSIGNED
                if old_user
                else NotificationEventType.TASK_ASSIGNED
            )
            trigger_notification_event(
                event_type=event_type,
                recipient=new_user,
                context={
                    "user_name": new_user.get_full_name() or new_user.username,
                    "employee_name": request.user.get_full_name()
                    or request.user.username,
                    "task_title": task.task_title,
                    "due_date": str(task.due_date) if task.due_date else "N/A",
                },
            )

            logger.info(
                "Task assigned successfully: "
                "task_id=%s old_user_id=%s "
                "new_user_id=%s performed_by=%s",
                task.task_id,
                old_user.pk if old_user else None,
                new_user.pk,
                request.user.pk,
            )

            return Response(
                {
                    "message": ("Task assigned successfully."),
                    "task_id": task.task_id,
                    "previous_assigned_to": (old_user.pk if old_user else None),
                    "assigned_to": new_user.pk,
                },
                status=status.HTTP_200_OK,
            )

        except (Http404, APIException):
            raise

        except Exception:
            logger.exception(
                "Error while assigning task: task_id=%s user_id=%s",
                task_id,
                request.user.pk,
            )

            return Response(
                {"error": ("Something went wrong while assigning the task.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# CHANGE TASK STATUS
# ==========================================================


class TaskStatusUpdateView(APIView):
    """
    PATCH /api/tasks/<task_id>/status/

    Only users with task_update permission
    can change task status.
    """

    permission_classes = [
        IsAuthenticated,
        HasDynamicPermission,
    ]
    permission_classes = [CanCommunicateWithLead]
    permission_names = {
        "PATCH": "task_update",
    }

    @extend_schema(
        tags=["Tasks"],
        summary="Update task status",
        description="Update the status of a task. Only users with task_update permission can perform this action.",
        operation_id="task_status_update",
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=int,
                description="Task ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "status_id": {
                        "type": "integer",
                        "description": "New task status ID",
                    },
                },
                "required": ["status_id"],
            }
        },
        responses={
            200: inline_serializer(
                "TaskStatusUpdateSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "task_id": serializers.IntegerField(),
                    "previous_status": serializers.CharField(),
                    "new_status": serializers.CharField(),
                },
            ),
            400: inline_serializer(
                "TaskStatusUpdateErrorResponse",
                fields={"status_id": serializers.CharField()},
            ),
            404: inline_serializer(
                "TaskStatusUpdateNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "TaskStatusUpdateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def patch(self, request, task_id):
        try:
            task = get_object_or_404(Task, task_id=task_id, is_active=True)

            status_id = request.data.get("status_id")

            if not status_id:
                return Response(
                    {"status_id": ("This field is required.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_status = get_object_or_404(
                TaskStatus, status_id=status_id, is_active=True
            )

            old_status = task.status

            with transaction.atomic():
                task.status = new_status

                task.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

            if task.assigned_to and task.assigned_to != request.user:
                trigger_notification_event(
                    event_type=NotificationEventType.TASK_STATUS_CHANGED,
                    recipient=task.assigned_to,
                    context={
                        "user_name": task.assigned_to.get_full_name()
                        or task.assigned_to.username,
                        "employee_name": request.user.get_full_name()
                        or request.user.username,
                        "task_title": task.task_title,
                        "previous_status": old_status.status_name,
                        "new_status": new_status.status_name,
                    },
                )

            logger.info(
                "Task status updated successfully: "
                "task_id=%s old_status=%s "
                "new_status=%s user_id=%s",
                task.task_id,
                old_status.status_name,
                new_status.status_name,
                request.user.pk,
            )

            return Response(
                {
                    "message": ("Task status updated successfully."),
                    "task_id": task.task_id,
                    "previous_status": (old_status.status_name),
                    "new_status": (new_status.status_name),
                },
                status=status.HTTP_200_OK,
            )

        except (Http404, APIException):
            raise

        except Exception:
            logger.exception(
                "Error while updating task status: task_id=%s user_id=%s",
                task_id,
                request.user.pk,
            )

            return Response(
                {"error": ("Something went wrong while updating the task status.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# MEETING
# ==========================================================
class MeetingCreateView(APIView):
    """
    POST /api/meetings/

    Create a meeting.
    """

    permission_classes = [IsAuthenticated, CanCommunicateWithLead]
    permission_names = {
        "POST": "add_meeting",
    }

    @extend_schema(
        tags=["Meetings"],
        summary="Create a meeting",
        description="Create a new meeting. Auth: IsAuthenticated. Sends meeting creation emails to participants.",
        operation_id="meeting_create",
        request=MeetingSerializer,
        responses={
            201: MeetingSerializer,
            400: MeetingSerializer,
            500: inline_serializer(
                "MeetingCreateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        try:
            serializer = MeetingSerializer(
                data=request.data, context={"request": request}
            )
            if not serializer.is_valid():
                logger.warning(
                    "Meeting validation failed: user_id=%s errors=%s",
                    request.user.pk,
                    serializer.errors,
                )
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            meeting = serializer.save(created_by=request.user)
            send_meeting_creation_emails(meeting)
            logger.info(
                "Meeting created successfully: meeting_id=%s user_id=%s",
                meeting.meeting_id,
                request.user.pk,
            )

            # Notify the task assignee about meeting creation.
            if (
                meeting.task_id
                and meeting.task_id.assigned_to
                and meeting.task_id.assigned_to != request.user
            ):
                trigger_notification_event(
                    event_type=NotificationEventType.MEETING_CREATED,
                    recipient=meeting.task_id.assigned_to,
                    context={
                        "user_name": meeting.task_id.assigned_to.get_full_name()
                        or meeting.task_id.assigned_to.username,
                        "employee_name": request.user.get_full_name()
                        or request.user.username,
                        "meeting_title": meeting.meeting_title,
                        "meeting_date": str(meeting.meeting_date),
                        "start_time": str(meeting.start_time),
                    },
                )

            return Response(
                MeetingSerializer(meeting, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while creating meeting: user_id=%s", request.user.pk
            )
            return Response(
                {"error": "Something went wrong while creating the meeting."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MeetingDetailView(APIView):
    """
    GET /api/meetings/<meeting_id>/
    Get meeting details.
    """

    permission_classes = [IsAuthenticated, CanCommunicateWithLead]
    permission_names = {
        "GET": "view_meeting",
    }

    @extend_schema(
        tags=["Meetings"],
        summary="Retrieve meeting details",
        description="Retrieve details of a specific meeting. Permission: view_meeting.",
        operation_id="meeting_retrieve",
        parameters=[
            OpenApiParameter(
                name="meeting_id",
                type=int,
                description="Meeting ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: MeetingSerializer,
            403: inline_serializer(
                "MeetingDetailForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "MeetingDetailNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "MeetingDetailServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def get(self, request, meeting_id):
        try:
            meeting = get_object_or_404(
                Meeting.objects.select_related(
                    "task_id",
                    "meeting_status_id",
                    "meeting_type_id",
                    "created_by",
                ),
                meeting_id=meeting_id,
                is_active=True,
            )
            self.check_object_permissions(request, meeting)
            serializer = MeetingSerializer(meeting, context={"request": request})
            logger.info(
                "Meeting fetched successfully: meeting_id=%s user_id=%s",
                meeting.meeting_id,
                request.user.pk,
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while fetching meeting: meeting_id=%s user_id=%s",
                meeting_id,
                request.user.pk,
            )
            return Response(
                {"error": "Something went wrong while fetching the meeting."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# RESCHEDULE MEETING
# ==========================================================


class MeetingRescheduleView(APIView):
    """
    PATCH /api/meetings/<meeting_id>/reschedule/

    Change meeting date/time.
    """

    permission_classes = [IsAuthenticated, CanCommunicateWithLead]
    permission_names = {
        "PATCH": "change_meeting",
    }

    @extend_schema(
        tags=["Meetings"],
        summary="Reschedule a meeting",
        description="Reschedule a meeting by changing its date and/or time. At least one of meeting_date, start_time, or end_time must be provided. Permission: change_meeting.",
        operation_id="meeting_reschedule",
        parameters=[
            OpenApiParameter(
                name="meeting_id",
                type=int,
                description="Meeting ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "meeting_date": {
                        "type": "string",
                        "format": "date",
                        "description": "New meeting date (YYYY-MM-DD)",
                    },
                    "start_time": {
                        "type": "string",
                        "format": "time",
                        "description": "New start time (HH:MM:SS)",
                    },
                    "end_time": {
                        "type": "string",
                        "format": "time",
                        "description": "New end time (HH:MM:SS)",
                    },
                },
            }
        },
        responses={
            200: inline_serializer(
                "MeetingRescheduleSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "meeting": MeetingSerializer(),
                },
            ),
            400: inline_serializer(
                "MeetingRescheduleErrorResponse",
                fields={"error": serializers.CharField()},
            ),
            403: inline_serializer(
                "MeetingRescheduleForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "MeetingRescheduleNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "MeetingRescheduleServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def patch(self, request, meeting_id):
        try:
            meeting = get_object_or_404(Meeting, meeting_id=meeting_id, is_active=True)
            self.check_object_permissions(request, meeting)

            reschedule_data = {}
            for field in ("meeting_date", "start_time", "end_time"):
                if field in request.data:
                    reschedule_data[field] = request.data[field]

            if not reschedule_data:
                return Response(
                    {
                        "error": "At least one of meeting_date, start_time, or end_time is required."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = MeetingSerializer(
                meeting,
                data=reschedule_data,
                partial=True,
                context={"request": request},
            )
            if not serializer.is_valid():
                logger.warning(
                    "Meeting reschedule validation failed: "
                    "meeting_id=%s user_id=%s errors=%s",
                    meeting_id,
                    request.user.pk,
                    serializer.errors,
                )
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                meeting = serializer.save()
            logger.info(
                "Meeting rescheduled successfully: meeting_id=%s user_id=%s",
                meeting.meeting_id,
                request.user.pk,
            )
            return Response(
                {
                    "message": "Meeting rescheduled successfully.",
                    "meeting": MeetingSerializer(
                        meeting, context={"request": request}
                    ).data,
                },
                status=status.HTTP_200_OK,
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while rescheduling meeting: meeting_id=%s user_id=%s",
                meeting_id,
                request.user.pk,
            )
            return Response(
                {"error": "Something went wrong while rescheduling the meeting."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# CHANGE MEETING STATUS
# ==========================================================


class MeetingStatusUpdateView(APIView):
    """
    PATCH /api/meetings/<meeting_id>/status/

    Change meeting status.
    """

    permission_classes = [IsAuthenticated, CanCommunicateWithLead]
    permission_names = {
        "PATCH": "change_meeting",
    }

    @extend_schema(
        tags=["Meetings"],
        summary="Update meeting status",
        description="Update the status of a meeting. Permission: change_meeting.",
        operation_id="meeting_status_update",
        parameters=[
            OpenApiParameter(
                name="meeting_id",
                type=int,
                description="Meeting ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "meeting_status_id": {
                        "type": "integer",
                        "description": "New meeting status ID",
                    },
                },
                "required": ["meeting_status_id"],
            }
        },
        responses={
            200: inline_serializer(
                "MeetingStatusUpdateSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "meeting_id": serializers.IntegerField(),
                    "previous_status": serializers.CharField(),
                    "new_status": serializers.CharField(),
                },
            ),
            400: inline_serializer(
                "MeetingStatusUpdateErrorResponse",
                fields={"meeting_status_id": serializers.CharField()},
            ),
            403: inline_serializer(
                "MeetingStatusUpdateForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "MeetingStatusUpdateNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "MeetingStatusUpdateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def patch(self, request, meeting_id):
        try:
            meeting = get_object_or_404(
                Meeting.objects.select_related("meeting_status_id"),
                meeting_id=meeting_id,
                is_active=True,
            )
            self.check_object_permissions(request, meeting)
            status_id = request.data.get("meeting_status_id")

            if not status_id:
                logger.warning(
                    "Meeting status update failed: status_id missing "
                    "meeting_id=%s user_id=%s",
                    meeting_id,
                    request.user.pk,
                )
                return Response(
                    {"meeting_status_id": "This field is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_status = get_object_or_404(
                MeetingStatus, meeting_status_id=status_id, is_active=True
            )

            old_status = meeting.meeting_status_id
            meeting.meeting_status_id = new_status
            meeting.save(update_fields=["meeting_status_id", "updated_at"])

            logger.info(
                "Meeting status updated successfully: "
                "meeting_id=%s previous_status=%s new_status=%s user_id=%s",
                meeting.meeting_id,
                old_status.status_name,
                new_status.status_name,
                request.user.pk,
            )

            return Response(
                {
                    "message": "Meeting status updated successfully.",
                    "meeting_id": meeting.meeting_id,
                    "previous_status": old_status.status_name,
                    "new_status": new_status.status_name,
                },
                status=status.HTTP_200_OK,
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while updating meeting status: meeting_id=%s user_id=%s",
                meeting_id,
                request.user.pk,
            )
            return Response(
                {"error": "Something went wrong while updating the meeting status."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# ADD MEETING PARTICIPANT
# ==========================================================


class MeetingParticipantAddView(APIView):
    """
    POST /api/meetings/<meeting_id>/participants/

    Add a participant.
    """

    permission_classes = [IsAuthenticated, CanCommunicateWithLead]
    permission_names = {
        "POST": "add_meeting_participant",
    }

    @extend_schema(
        tags=["Meetings"],
        summary="Add a participant to a meeting",
        description="Add a participant to a meeting. Permission: add_meeting_participant.",
        operation_id="meeting_participant_add",
        parameters=[
            OpenApiParameter(
                name="meeting_id",
                type=int,
                description="Meeting ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "User ID of the participant to add",
                    },
                    "participant_role": {
                        "type": "string",
                        "description": "Role of the participant in the meeting",
                    },
                    "is_required": {
                        "type": "boolean",
                        "description": "Whether the participant is required (default: true)",
                    },
                },
                "required": ["user_id", "participant_role"],
            }
        },
        responses={
            201: MeetingParticipantSerializer,
            400: inline_serializer(
                "MeetingParticipantAddErrorResponse",
                fields={"user_id": serializers.CharField()},
            ),
            403: inline_serializer(
                "MeetingParticipantAddForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "MeetingParticipantAddNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "MeetingParticipantAddServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request, meeting_id):
        try:
            meeting = get_object_or_404(Meeting, meeting_id=meeting_id)
            self.check_object_permissions(request, meeting)
            user_id = request.data.get("user_id")
            participant_role = request.data.get("participant_role")
            is_required = request.data.get("is_required", True)

            # --------------------------------------------------
            # USER ID VALIDATION
            # --------------------------------------------------
            if not user_id:
                logger.warning(
                    "Add participant failed: user_id missing "
                    "meeting_id=%s performed_by=%s",
                    meeting_id,
                    request.user.pk,
                )
                return Response(
                    {"user_id": "This field is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --------------------------------------------------
            # PARTICIPANT ROLE VALIDATION
            # --------------------------------------------------
            if not participant_role:
                logger.warning(
                    "Add participant failed: participant_role missing "
                    "meeting_id=%s user_id=%s performed_by=%s",
                    meeting_id,
                    user_id,
                    request.user.pk,
                )
                return Response(
                    {"participant_role": ("This field is required.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --------------------------------------------------
            # GET USER
            # --------------------------------------------------
            user = get_object_or_404(User, pk=user_id)

            # --------------------------------------------------
            # CHECK DUPLICATE PARTICIPANT
            # --------------------------------------------------
            already_exists = MeetingParticipant.objects.filter(
                meeting_id=meeting, user_id=user
            ).exists()

            if already_exists:
                logger.warning(
                    "Duplicate participant attempt: "
                    "meeting_id=%s user_id=%s performed_by=%s",
                    meeting_id,
                    user_id,
                    request.user.pk,
                )
                return Response(
                    {"error": ("This user is already a participant of this meeting.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --------------------------------------------------
            # CREATE PARTICIPANT
            # --------------------------------------------------
            participant = MeetingParticipant.objects.create(
                meeting_id=meeting,
                user_id=user,
                participant_role=participant_role.strip(),
                is_required=is_required,
            )

            logger.info(
                "Meeting participant added successfully: "
                "participant_id=%s meeting_id=%s user_id=%s performed_by=%s",
                participant.pk,
                meeting.meeting_id,
                user.pk,
                request.user.pk,
            )

            # --------------------------------------------------
            # SERIALIZE RESPONSE
            # --------------------------------------------------
            serializer = MeetingParticipantSerializer(
                participant, context={"request": request}
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while adding meeting participant: meeting_id=%s performed_by=%s",
                meeting_id,
                request.user.pk,
            )
            return Response(
                {
                    "error": (
                        "Something went wrong while adding the meeting participant."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# REMOVE MEETING PARTICIPANT
# ==========================================================


class MeetingParticipantRemoveView(APIView):
    """
    DELETE /api/meetings/<meeting_id>/participants/<user_id>/

    Remove participant from meeting.
    """

    permission_classes = [IsAuthenticated, CanCommunicateWithLead]
    permission_names = {
        "DELETE": "delete_meeting_participant",
    }

    @extend_schema(
        tags=["Meetings"],
        summary="Remove a participant from a meeting",
        description="Remove a participant from a meeting. Permission: delete_meeting_participant.",
        operation_id="meeting_participant_remove",
        parameters=[
            OpenApiParameter(
                name="meeting_id",
                type=int,
                description="Meeting ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="user_id",
                type=str,
                description="User ID of the participant to remove",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: inline_serializer(
                "MeetingParticipantRemoveSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "meeting_id": serializers.IntegerField(),
                    "user_id": serializers.CharField(),
                },
            ),
            403: inline_serializer(
                "MeetingParticipantRemoveForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "MeetingParticipantRemoveNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "MeetingParticipantRemoveServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def delete(self, request, meeting_id, user_id):
        try:
            meeting = get_object_or_404(Meeting, meeting_id=meeting_id)
            self.check_object_permissions(request, meeting)
            participant = get_object_or_404(
                MeetingParticipant, meeting_id=meeting, user_id_id=user_id
            )

            participant.delete()

            logger.info(
                "Meeting participant removed successfully: "
                "meeting_id=%s user_id=%s performed_by=%s",
                meeting.meeting_id,
                user_id,
                request.user.pk,
            )

            return Response(
                {
                    "message": "Participant removed successfully.",
                    "meeting_id": meeting.meeting_id,
                    "user_id": user_id,
                },
                status=status.HTTP_200_OK,
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while removing meeting participant: "
                "meeting_id=%s user_id=%s performed_by=%s",
                meeting_id,
                user_id,
                request.user.pk,
            )
            return Response(
                {
                    "error": (
                        "Something went wrong while removing the meeting participant."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# REMINDER
# ==========================================================


class ReminderCreateView(APIView):
    """
    POST /api/reminders/

    Create a reminder.
    """

    permission_classes = [IsAuthenticated, CanCommunicateWithLead]
    permission_names = {
        "POST": "add_reminder",
    }

    @extend_schema(
        tags=["Reminders"],
        summary="Create a reminder",
        description="Create a new reminder. Auth: IsAuthenticated.",
        operation_id="reminder_create",
        request=ReminderSerializer,
        responses={
            201: ReminderSerializer,
            400: ReminderSerializer,
            500: inline_serializer(
                "ReminderCreateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        try:
            serializer = ReminderSerializer(
                data=request.data, context={"request": request}
            )
            if not serializer.is_valid():
                logger.warning(
                    "Reminder validation failed: user_id=%s errors=%s",
                    request.user.pk,
                    serializer.errors,
                )
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            reminder = serializer.save(created_by=request.user)

            logger.info(
                "Reminder created successfully: reminder_id=%s user_id=%s",
                reminder.reminder_id,
                request.user.pk,
            )

            try:
                if reminder.reminder_for and reminder.reminder_for != request.user:
                    trigger_notification_event(
                        event_type=NotificationEventType.REMINDER_CREATED,
                        recipient=reminder.reminder_for,
                        context={
                            "user_name": reminder.reminder_for.get_full_name()
                            or reminder.reminder_for.username,
                            "employee_name": request.user.get_full_name()
                            or request.user.username,
                            "message": reminder.message[:100],
                            "reminder_datetime": str(reminder.reminder_datetime),
                        },
                    )
            except Exception:
                logger.exception("Failed to send reminder creation notification")

            return Response(
                ReminderSerializer(reminder, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while creating reminder: user_id=%s", request.user.pk
            )
            return Response(
                {"error": ("Something went wrong while creating the reminder.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReminderDetailView(APIView):
    """
    GET    /api/reminders/<reminder_id>/
        Reminder detail

    PATCH  /api/reminders/<reminder_id>/
        Update reminder

    DELETE /api/reminders/<reminder_id>/
        Delete reminder
    """

    permission_classes = [IsAuthenticated, CanCommunicateWithLead]
    permission_names = {
        "GET": "view_reminder",
        "PATCH": "change_reminder",
        "DELETE": "delete_reminder",
    }

    def get_reminder(self, reminder_id):
        return get_object_or_404(
            Reminder.objects.select_related(
                "task_id",
                "meeting_id",
                "reminder_type_id",
                "reminder_status_id",
                "created_by",
            ),
            reminder_id=reminder_id,
            is_active=True,
        )

    # ------------------------------------------------------
    # REMINDER DETAIL
    # ------------------------------------------------------
    @extend_schema(
        tags=["Reminders"],
        summary="Retrieve reminder detail",
        description="Retrieve reminder detail. Permission: view_reminder.",
        operation_id="reminder_retrieve",
        parameters=[
            OpenApiParameter(
                name="reminder_id",
                type=int,
                description="Reminder ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: ReminderSerializer,
            403: inline_serializer(
                "ReminderDetailForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "ReminderDetailNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "ReminderDetailServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def get(self, request, reminder_id):
        try:
            reminder = self.get_reminder(reminder_id)
            self.check_object_permissions(request, reminder)

            serializer = ReminderSerializer(reminder, context={"request": request})

            logger.info(
                "Reminder fetched successfully: reminder_id=%s user_id=%s",
                reminder.reminder_id,
                request.user.pk,
            )

            return Response(serializer.data, status=status.HTTP_200_OK)
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while fetching reminder: reminder_id=%s user_id=%s",
                reminder_id,
                request.user.pk,
            )
            return Response(
                {"error": ("Something went wrong while fetching the reminder.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------
    # UPDATE REMINDER
    # ------------------------------------------------------
    @extend_schema(
        tags=["Reminders"],
        summary="Partially update a reminder",
        description="Update a reminder. Permission: change_reminder.",
        operation_id="reminder_partial_update",
        parameters=[
            OpenApiParameter(
                name="reminder_id",
                type=int,
                description="Reminder ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        request=ReminderSerializer,
        responses={
            200: ReminderSerializer,
            400: ReminderSerializer,
            403: inline_serializer(
                "ReminderUpdateForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "ReminderUpdateNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "ReminderUpdateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def patch(self, request, reminder_id):
        try:
            reminder = self.get_reminder(reminder_id)
            self.check_object_permissions(request, reminder)

            serializer = ReminderSerializer(
                reminder, data=request.data, partial=True, context={"request": request}
            )

            if not serializer.is_valid():
                logger.warning(
                    "Reminder update validation failed: "
                    "reminder_id=%s user_id=%s errors=%s",
                    reminder_id,
                    request.user.pk,
                    serializer.errors,
                )
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            reminder = serializer.save()

            logger.info(
                "Reminder updated successfully: reminder_id=%s user_id=%s",
                reminder.reminder_id,
                request.user.pk,
            )

            return Response(
                ReminderSerializer(reminder, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while updating reminder: reminder_id=%s user_id=%s",
                reminder_id,
                request.user.pk,
            )
            return Response(
                {"error": ("Something went wrong while updating the reminder.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------
    # DELETE REMINDER
    # ------------------------------------------------------
    @extend_schema(
        tags=["Reminders"],
        summary="Delete a reminder",
        description="Delete a reminder. Permission: delete_reminder.",
        operation_id="reminder_delete",
        parameters=[
            OpenApiParameter(
                name="reminder_id",
                type=int,
                description="Reminder ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: inline_serializer(
                "ReminderDeleteSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "reminder_id": serializers.IntegerField(),
                },
            ),
            403: inline_serializer(
                "ReminderDeleteForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "ReminderDeleteNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "ReminderDeleteServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def delete(self, request, reminder_id):
        try:
            reminder = self.get_reminder(reminder_id)
            self.check_object_permissions(request, reminder)

            reminder.delete()

            logger.info(
                "Reminder deleted successfully: reminder_id=%s user_id=%s",
                reminder_id,
                request.user.pk,
            )

            return Response(
                {
                    "message": "Reminder deleted successfully.",
                    "reminder_id": reminder_id,
                },
                status=status.HTTP_200_OK,
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while deleting reminder: reminder_id=%s user_id=%s",
                reminder_id,
                request.user.pk,
            )
            return Response(
                {"error": ("Something went wrong while deleting the reminder.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# CHANGE REMINDER STATUS
# ==========================================================


class ReminderStatusUpdateView(APIView):
    """
    PATCH /api/reminders/<reminder_id>/status/

    Change reminder status.
    """

    permission_classes = [IsAuthenticated, CanCommunicateWithLead]
    permission_names = {
        "PATCH": "change_reminder",
    }

    @extend_schema(
        tags=["Reminders"],
        summary="Update reminder status",
        description="Update the status of a reminder. Permission: change_reminder.",
        operation_id="reminder_status_update",
        parameters=[
            OpenApiParameter(
                name="reminder_id",
                type=int,
                description="Reminder ID",
                required=True,
                location=OpenApiParameter.PATH,
            ),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "reminder_status_id": {
                        "type": "integer",
                        "description": "New reminder status ID",
                    },
                },
                "required": ["reminder_status_id"],
            }
        },
        responses={
            200: inline_serializer(
                "ReminderStatusUpdateSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "reminder_id": serializers.IntegerField(),
                    "previous_status": serializers.CharField(),
                    "new_status": serializers.CharField(),
                },
            ),
            400: inline_serializer(
                "ReminderStatusUpdateErrorResponse",
                fields={"reminder_status_id": serializers.CharField()},
            ),
            403: inline_serializer(
                "ReminderStatusUpdateForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "ReminderStatusUpdateNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "ReminderStatusUpdateServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def patch(self, request, reminder_id):
        try:
            reminder = get_object_or_404(
                Reminder.objects.select_related("reminder_status_id"),
                reminder_id=reminder_id,
                is_active=True,
            )
            self.check_object_permissions(request, reminder)
            status_id = request.data.get("reminder_status_id")

            if not status_id:
                logger.warning(
                    "Reminder status update failed: "
                    "status_id missing reminder_id=%s user_id=%s",
                    reminder_id,
                    request.user.pk,
                )
                return Response(
                    {"reminder_status_id": ("This field is required.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_status = get_object_or_404(
                ReminderStatus, reminder_status_id=status_id, is_active=True
            )

            old_status = reminder.reminder_status_id
            reminder.reminder_status_id = new_status
            reminder.save(update_fields=["reminder_status_id", "updated_at"])

            logger.info(
                "Reminder status updated successfully: "
                "reminder_id=%s previous_status=%s "
                "new_status=%s user_id=%s",
                reminder.reminder_id,
                old_status.status_name,
                new_status.status_name,
                request.user.pk,
            )

            return Response(
                {
                    "message": ("Reminder status updated successfully."),
                    "reminder_id": reminder.reminder_id,
                    "previous_status": old_status.status_name,
                    "new_status": new_status.status_name,
                },
                status=status.HTTP_200_OK,
            )
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception(
                "Error while updating reminder status: reminder_id=%s user_id=%s",
                reminder_id,
                request.user.pk,
            )
            return Response(
                {"error": ("Something went wrong while updating the reminder status.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
