from django.urls import path

from .views import (
    FollowUpListCreateView,
    FollowUpDetailView,
)

urlpatterns = [
    # ======================================================
    # FOLLOWUP
    # ======================================================
    # FollowUp
    path("", FollowUpListCreateView.as_view(), name="followup-list-create"),
    path("<int:followup_id>/", FollowUpDetailView.as_view(), name="followup-detail"),
]
