from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    # Task
    TaskListCreateView,
    TaskDetailView,
    TaskAssignView,
    TaskStatusUpdateView,

    # Meeting
    MeetingStatusViewSet,
    MeetingParticipantViewSet,
    MeetingTypeViewSet,
    MeetingViewSet,

    # Reminder
    ReminderTypeViewSet,
    ReminderStatusViewSet,
    ReminderViewSet,
)


router = DefaultRouter()

router.register(
    r"meeting",
    MeetingViewSet,
    basename="meeting"
)

router.register(
    r"meeting-participant",
    MeetingParticipantViewSet,
    basename="meeting-participant"
)

router.register(
    r"meeting-status",
    MeetingStatusViewSet,
    basename="meeting-status"
)

router.register(
    r"meeting-type",
    MeetingTypeViewSet,
    basename="meeting-type"
)

router.register(
    r"reminder",
    ReminderViewSet,
    basename="reminder"
)

router.register(
    r"reminder-type",
    ReminderTypeViewSet,
    basename="reminder-type"
)

router.register(
    r"reminder-status",
    ReminderStatusViewSet,
    basename="reminder-status"
)


urlpatterns = [

    # ======================================================
    # TASK
    # ======================================================

    path(
        "",
        TaskListCreateView.as_view(),
        name="task-list-create"
    ),

    path(
        "<int:task_id>/",
        TaskDetailView.as_view(),
        name="task-detail"
    ),

    path(
        "<int:task_id>/assign/",
        TaskAssignView.as_view(),
        name="task-assign"
    ),

    path(
        "<int:task_id>/status/",
        TaskStatusUpdateView.as_view(),
        name="task-status-update"
    ),

    # ======================================================
    # VIEWSETS
    # ======================================================

    path(
        "",
        include(router.urls)
    ),
]