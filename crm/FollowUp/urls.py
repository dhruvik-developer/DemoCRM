from django.urls import path

from .views import (
    FollowUpListCreateView,
    FollowUpDetailView,
    FollowUpNoteCreateView,
    UserNotificationListView,
    NotificationDetailView,
)


urlpatterns = [

    # ======================================================
    # FOLLOWUP
    # ======================================================

    path(
        "followups/",
        FollowUpListCreateView.as_view(),
        name="followup-list-create"
    ),

    path(
        "followups/<int:followup_id>/",
        FollowUpDetailView.as_view(),
        name="followup-detail"
    ),

    path(
        "followups/<int:followup_id>/notes/",
        FollowUpNoteCreateView.as_view(),
        name="followup-add-note"
    ),

    # ======================================================
    # NOTIFICATION
    # ======================================================

    path(
        "notifications/",
        UserNotificationListView.as_view(),
        name="notification-list"
    ),

    path(
        "notifications/<int:notification_id>/",
        NotificationDetailView.as_view(),
        name="notification-detail"
    ),
]