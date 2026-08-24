from django.urls import path

from .views import (
    FollowUpListCreateView,
    FollowUpDetailView,
    FollowUpStatusUpdateView
)

urlpatterns = [
    # ======================================================
    # FOLLOWUP
    # ======================================================
    # FollowUp
    path("", FollowUpListCreateView.as_view(), name="followup-list-create"),
    path("<int:followup_id>/", FollowUpDetailView.as_view(), name="followup-detail"),
    path(
    "<int:followup_id>/status/",
    FollowUpStatusUpdateView.as_view(),
    name="followup-status-update",
),
]
