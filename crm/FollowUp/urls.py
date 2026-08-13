from django.urls import path
from . import views
urlpatterns = [

    # List all follow-ups / Create follow-up
    path("",views.followup_list_create,name="followup_list_create",),
    # Follow-up detail
    path("<int:followup_id>/",views.followup_detail,name="followup_detail",),

    # List notes / Create note
    path(
        "notes/",
        views.followup_note_list_create,
        name="followup_note_list_create",
    ),

    # Note detail
    path("notes/<int:note_id>/",views.followup_note_detail,name="followup_note_detail",),

    # View activity logs
    path("activity-logs/",views.activity_log_list,name="activity_log_list",),

    # View single activity log
    path("activity-logs/<int:activity_id>/",views.activity_log_detail,name="activity_log_detail",),

    # List notifications
    path("notifications/",views.notification_list_create,name="notification_list_create",),

    # Notification detail
    path("notifications/<int:notification_id>/",views.notification_detail,name="notification_detail",),

    # Mark notification as read
    path("notifications/<int:notification_id>/read/",views.notification_mark_read,name="notification_mark_read",),
]