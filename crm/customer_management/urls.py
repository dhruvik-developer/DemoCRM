from django.urls import path

from .views import (
    ActivityListCreateView,
    AuditLogListView,
    CustomerDetailView,
    CustomerListCreateView,
    CustomerActivityListView,
    LeadAssignView,
    LeadConvertView,
    LeadDetailView,
    LeadListCreateView,
    LeadLostView,
    LeadProgressView,
    LeadReengageView,
    LeadSourceListCreateView,
    PipelineListCreateView,
    PipelineStageListCreateView,
)

urlpatterns = [
    # Lead Sources
    path(
        "lead-sources/",
        LeadSourceListCreateView.as_view(),
        name="lead-source-list-create",
    ),
    # Pipelines
    path(
        "pipelines/",
        PipelineListCreateView.as_view(),
        name="pipeline-list-create",
    ),
    # Pipeline Stages
    path(
        "pipeline-stages/",
        PipelineStageListCreateView.as_view(),
        name="pipeline-stage-list-create",
    ),
    # Leads
    path(
        "leads/",
        LeadListCreateView.as_view(),
        name="lead-list-create",
    ),
    path(
        "leads/<uuid:pk>/",
        LeadDetailView.as_view(),
        name="lead-detail",
    ),
    # Lead workflows
    path(
        "leads/<uuid:pk>/assign/",
        LeadAssignView.as_view(),
        name="lead-assign",
    ),
    path(
        "leads/<uuid:pk>/progress/",
        LeadProgressView.as_view(),
        name="lead-progress",
    ),
    path(
        "leads/<uuid:pk>/lost/",
        LeadLostView.as_view(),
        name="lead-lost",
    ),
    path(
        "leads/<uuid:pk>/reengage/",
        LeadReengageView.as_view(),
        name="lead-reengage",
    ),
    path(
        "leads/<uuid:pk>/convert/",
        LeadConvertView.as_view(),
        name="lead-convert",
    ),
    # Activities
    path(
        "activities/",
        ActivityListCreateView.as_view(),
        name="activity-list-create",
    ),
    # Audit Logs
    path(
        "audit-logs/",
        AuditLogListView.as_view(),
        name="audit-log-list",
    ),
    # Customers
    path(
        "customers/",
        CustomerListCreateView.as_view(),
        name="customer-list-create",
    ),
    path(
        "customers/<uuid:pk>/",
        CustomerDetailView.as_view(),
        name="customer-detail",
    ),
    path(
        "customers/<uuid:pk>/activities/",
        CustomerActivityListView.as_view(),
        name="customer-activity-list",
    ),
]
