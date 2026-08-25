from django.urls import path

from .views import (
    MeetingApprovalView,
    TaskListCreateView,
    TaskDetailView,
    TaskAssignView,
    TaskStatusUpdateView,
    MeetingCreateView,
    MeetingDetailView,
    MeetingRescheduleView,
    MeetingStatusUpdateView,
    MeetingParticipantAddView,
    MeetingParticipantRemoveView,
    ReminderCreateView,
    ReminderDetailView,
    ReminderStatusUpdateView,
)


urlpatterns = [
    # ======================================================
    # TASK
    # ======================================================
    path("", TaskListCreateView.as_view(), name="task-list-create"),
    path("<int:task_id>/", TaskDetailView.as_view(), name="task-detail"),
    path("<int:task_id>/assign/", TaskAssignView.as_view(), name="task-assign"),
    path(
        "<int:task_id>/status/",
        TaskStatusUpdateView.as_view(),
        name="task-status-update",
    ),
    # ======================================================
    # MEETING
    # ======================================================
    path(
        "meetings/",
        MeetingCreateView.as_view(),
        name="meeting-create",
    ),
    path(
        "meetings/<int:meeting_id>/",
        MeetingDetailView.as_view(),
        name="meeting-detail",
    ),
    path(
        "meetings/<int:meeting_id>/approval/",
        MeetingApprovalView.as_view(),
        name="meeting-approval",
    ),
    path(
        "meetings/<int:meeting_id>/",
        MeetingDetailView.as_view(),
        name="meeting-detail",
    ),
    path(
        "meetings/<int:meeting_id>/approval/",
        MeetingApprovalView.as_view(),
        name="meeting-approval",
    ),
    path(
        "meetings/<int:meeting_id>/reschedule/",
        MeetingRescheduleView.as_view(),
        name="meeting-reschedule",
    ),
    path(
        "meetings/<int:meeting_id>/status/",
        MeetingStatusUpdateView.as_view(),
        name="meeting-status-update",
    ),
    path(
        "meetings/<int:meeting_id>/participants/",
        MeetingParticipantAddView.as_view(),
        name="meeting-participant-add",
    ),
    path(
        "meetings/<int:meeting_id>/participants/<str:user_id>/",
        MeetingParticipantRemoveView.as_view(),
        name="meeting-participant-remove",
    ),
    # ======================================================
    # REMINDER
    # ======================================================
    path("reminders/", ReminderCreateView.as_view(), name="reminder-create"),
    path(
        "reminders/<int:reminder_id>/",
        ReminderDetailView.as_view(),
        name="reminder-detail",
    ),
    path(
        "reminders/<int:reminder_id>/status/",
        ReminderStatusUpdateView.as_view(),
        name="reminder-status-update",
    ),
]
