from django.urls import path

from .views import (
    FollowUpListCreateView,
    FollowUpDetailView,
    FollowUpNoteCreateView,
    UserNotificationListView,
    NotificationDetailView,
    NotificationTemplateListView,
    NotificationPreviewView,
    NotificationSendView,
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
        "notifications/preview/",
        NotificationPreviewView.as_view(),
        name="notification-preview"
    ),

    path(
        "notifications/send/",
        NotificationSendView.as_view(),
        name="notification-send"
    ),

    path(
        "notifications/<int:notification_id>/",
        NotificationDetailView.as_view(),
        name="notification-detail"
    ),

    path(
        "notification-templates/",
        NotificationTemplateListView.as_view(),
        name="notification-template-list"
    ),
]