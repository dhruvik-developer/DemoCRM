from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdhocFieldProposalViewSet,
    CallAttemptViewSet,
    CallTemplateViewSet,
    FormSubmissionViewSet,
    IndexedSubmissionValueViewSet,
    PipelineStageActivityViewSet,
    TaskTriggerRuleViewSet,
    TemplateFieldViewSet,
    TemplateVersionViewSet,
)

router = DefaultRouter()
router.register("templates", CallTemplateViewSet, basename="calltemplate")
router.register("versions", TemplateVersionViewSet, basename="templateversion")
router.register("fields", TemplateFieldViewSet, basename="templatefield")
router.register(
    "stage-activities", PipelineStageActivityViewSet, basename="pipelinestageactivity"
)
router.register("attempts", CallAttemptViewSet, basename="callattempt")
router.register("submissions", FormSubmissionViewSet, basename="formsubmission")
router.register("trigger-rules", TaskTriggerRuleViewSet, basename="tasktriggerrule")
router.register(
    "adhoc-proposals", AdhocFieldProposalViewSet, basename="adhocfieldproposal"
)
router.register(
    "indexed-values", IndexedSubmissionValueViewSet, basename="indexedsubmissionvalue"
)

urlpatterns = [
    path("", include(router.urls)),
]
