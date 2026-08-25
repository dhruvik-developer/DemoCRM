from django.urls import path
from .views import (
    NotificationTemplateListView,
    NotificationTemplateDetailView,
    ManualNotificationSendView,
    UserNotificationListView,
    UserNotificationDetailView,
    NotificationMarkReadView,
)

app_name = "Notification"

urlpatterns = [
    # Template Management APIs
    path(
        "notification-templates/",
        NotificationTemplateListView.as_view(),
        name="template-list-create",
    ),
    path(
        "notification-templates/<int:pk>/",
        NotificationTemplateDetailView.as_view(),
        name="template-detail",
    ),
    # Manual Notification API
    path(
        "notifications/send/",
        ManualNotificationSendView.as_view(),
        name="notification-send",
    ),
    # User Notification APIs
    path(
        "notifications/",
        UserNotificationListView.as_view(),
        name="user-notification-list",
    ),
    path(
        "notifications/<int:pk>/",
        UserNotificationDetailView.as_view(),
        name="user-notification-detail",
    ),
    path(
        "notifications/<int:pk>/read/",
        NotificationMarkReadView.as_view(),
        name="user-notification-mark-read",
    ),
]
