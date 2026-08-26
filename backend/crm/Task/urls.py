from django.urls import path

from .views import (
    TaskListCreateView,
    TaskDetailView,
    TaskAssignView,
    TaskStatusUpdateView,
    MeetingRescheduleView,
    MeetingStatusUpdateView,
    MeetingParticipantAddView,
    MeetingParticipantRemoveView,
    ReminderDetailView,
    ReminderStatusUpdateView,
    TaskStatusListView,
    TaskPriorityListView,
    TaskCategoryListView,
    MeetingStatusListView,
    MeetingTypeListView,
    ReminderTypeListView,
    ReminderStatusListView,
)


urlpatterns = [
    # ======================================================
    # MASTER DATA (enum dropdowns)
    # ======================================================
    path(
        "master/task-statuses/",
        TaskStatusListView.as_view(),
        name="task-status-list",
    ),
    path(
        "master/task-priorities/",
        TaskPriorityListView.as_view(),
        name="task-priority-list",
    ),
    path(
        "master/task-categories/",
        TaskCategoryListView.as_view(),
        name="task-category-list",
    ),
    path(
        "master/meeting-statuses/",
        MeetingStatusListView.as_view(),
        name="meeting-status-list",
    ),
    path(
        "master/meeting-types/",
        MeetingTypeListView.as_view(),
        name="meeting-type-list",
    ),
    path(
        "master/reminder-types/",
        ReminderTypeListView.as_view(),
        name="reminder-type-list",
    ),
    path(
        "master/reminder-statuses/",
        ReminderStatusListView.as_view(),
        name="reminder-status-list",
    ),
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
