from django.urls import path

from .views import (
    FollowUpListCreateView,
    FollowUpDetailView,
    FollowUpNoteCreateView,
)


urlpatterns = [
    # ======================================================
    # FOLLOWUP
    # ======================================================
    # FollowUp
    path("", FollowUpListCreateView.as_view(), name="followup-list-create"),
    path("<int:followup_id>/", FollowUpDetailView.as_view(), name="followup-detail"),
    path(
        "<int:followup_id>/notes/",
        FollowUpNoteCreateView.as_view(),
        name="followup-add-note",
    ),
    # path(
    #     "followups/notes/<int:note_id>/",
    #     FollowUpNoteDetailView.as_view(),
    #     name="followup-note-detail",
    # ),
]
