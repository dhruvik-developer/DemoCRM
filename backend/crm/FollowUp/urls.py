from django.urls import path

from .views import FollowUpListCreateView, FollowUpDetailView, FollowUpStatusUpdateView, RecordNoteListCreateView, FollowUpKPIView

urlpatterns = [
    path("notes/", RecordNoteListCreateView.as_view(), name="record-note-list-create"),
    # ======================================================
    # FOLLOWUP
    # ======================================================
    # FollowUp
    path("", FollowUpListCreateView.as_view(), name="followup-list-create"),
    path("kpi/", FollowUpKPIView.as_view(), name="followup-kpi"),
    path("<int:followup_id>/", FollowUpDetailView.as_view(), name="followup-detail"),
    path(
        "<int:followup_id>/status/",
        FollowUpStatusUpdateView.as_view(),
        name="followup-status-update",
    ),
]
