from django.urls import path

from . import views

urlpatterns = [
    # ---------------- TASK ----------------
    path("", views.task_list_create, name="task_list_create"),
    path("<int:task_id>/", views.task_detail, name="task_detail"),
    path("<int:task_id>/assign/", views.assign_task, name="assign_task"),
    path("<int:task_id>/status/", views.task_status_update, name="task_status_update"),

    path("statuses/", views.task_status_list_create, name="task_status_list_create"),
    path("priorities/", views.task_priority_list_create, name="task_priority_list_create"),
    path("categories/", views.task_category_list_create, name="task_category_list_create"),

    # ---------------- MEETING ----------------
    path("meetings/", views.meeting_list_create, name="meeting_list_create"),
    path("meetings/<int:meeting_id>/", views.meeting_detail, name="meeting_detail"),
    path("meeting-participants/", views.meeting_participant_list_create, name="meeting_participant_list_create"),
    path("meeting-statuses/", views.meeting_status_list_create, name="meeting_status_list_create"),
    path("meeting-statuses/<int:meeting_status_id>/", views.meeting_status_detail, name="meeting_status_detail"),
    path("meeting-types/", views.meeting_type_list_create, name="meeting_type_list_create"),
    path("meeting-types/<int:meeting_type_id>/", views.meeting_type_detail, name="meeting_type_detail"),

    # ---------------- REMINDER ----------------
    path("reminders/", views.reminder_list_create, name="reminder_list_create"),
    path("reminders/<int:reminder_id>/", views.reminder_detail, name="reminder_detail"),
    path("reminder-types/", views.reminder_type_list_create, name="reminder_type_list_create"),
    path("reminder-types/<int:reminder_type_id>/", views.reminder_type_detail, name="reminder_type_detail"),
    path("reminder-statuses/", views.reminder_status_list_create, name="reminder_status_list_create"),
    path("reminder-statuses/<int:reminder_status_id>/", views.reminder_status_detail, name="reminder_status_detail"),

    # ---------------- DASHBOARD ----------------
    path("dashboard/", views.dashboard_report, name="dashboard_report"),
]