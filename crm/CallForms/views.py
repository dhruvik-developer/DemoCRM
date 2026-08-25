import logging
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from .models import (
    AdhocFieldProposal,
    CallAttempt,
    CallTemplate,
    FormSubmission,
    IndexedSubmissionValue,
    PipelineStageActivity,
    TaskTriggerRule,
    TemplateField,
    TemplateVersion,
)
from .permissions import CallFormsHasPermission
from .serializers import (
    AdhocFieldProposalSerializer,
    CallAttemptSerializer,
    CallTemplateDetailSerializer,
    CallTemplateSerializer,
    CloneVersionSerializer,
    CreateTemplateSerializer,
    FormSubmissionSerializer,
    IndexedSubmissionValueSerializer,
    LogCallAttemptSerializer,
    PipelineStageActivityDetailSerializer,
    PipelineStageActivitySerializer,
    ReorderFieldsSerializer,
    ReviewAdhocFieldProposalSerializer,
    SubmitCallFormSerializer,
    TaskTriggerRuleSerializer,
    TemplateFieldSerializer,
    TemplateVersionDetailSerializer,
    TemplateVersionSerializer,
)
from .services import (
    clone_template_version,
    create_template_with_initial_version,
    filter_submissions_by_field_value,
    get_lead_stage_primary_form,
    get_lead_timeline_feed,
    get_template_version_analytics,
    log_call_attempt,
    propose_adhoc_field,
    reorder_template_fields,
    review_adhoc_field,
    set_primary_stage_activity,
    set_primary_version,
    submit_call_form,
)

logger = logging.getLogger(__name__)


@extend_schema(tags=["CallForms Templates"])
class CallTemplateViewSet(viewsets.ModelViewSet):
    queryset = CallTemplate.objects.all().prefetch_related("versions")
    permission_classes = [IsAuthenticated, CallFormsHasPermission]
    permission_names = {
        "GET": "view_calltemplate",
        "POST": "add_calltemplate",
        "PUT": "change_calltemplate",
        "PATCH": "change_calltemplate",
        "DELETE": "delete_calltemplate",
    }

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CallTemplateDetailSerializer
        if self.action == "create":
            return CreateTemplateSerializer
        return CallTemplateSerializer

    def create(self, request, *args, **kwargs):
        serializer = CreateTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        template, version = create_template_with_initial_version(
            name=data["name"],
            description=data.get("description", ""),
            created_by=request.user,
            initial_fields=data.get("initial_fields", []),
        )

        response_serializer = CallTemplateDetailSerializer(template)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="set-primary")
    def set_primary_version_action(self, request, pk=None):
        template = self.get_object()
        version_id = request.data.get("version_id")

        if not version_id:
            return Response(
                {"error": "version_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            version = set_primary_version(template, version_id)
            return Response(
                TemplateVersionSerializer(version).data,
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="create-version")
    def create_version_action(self, request, pk=None):
        template = self.get_object()
        from_version_id = request.data.get("from_version_id")
        set_primary = request.data.get("set_primary", True)
        version_label = request.data.get("version_label")

        try:
            if from_version_id:
                version = clone_template_version(
                    source_version_or_id=from_version_id,
                    created_by=request.user,
                    new_label=version_label,
                    set_primary=set_primary,
                )
            else:
                max_num = (
                    template.versions.aggregate(max_num=models.Max("version_number"))[
                        "max_num"
                    ]
                    or 0
                )
                next_num = max_num + 1
                if set_primary:
                    template.versions.update(is_primary=False)
                version = TemplateVersion.objects.create(
                    template=template,
                    version_number=next_num,
                    version_label=version_label or f"v{next_num}.0",
                    is_primary=set_primary,
                    created_by=request.user,
                )

            return Response(
                TemplateVersionDetailSerializer(version).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["CallForms Templates"])
class TemplateVersionViewSet(viewsets.ModelViewSet):
    queryset = TemplateVersion.objects.all().prefetch_related("fields")
    permission_classes = [IsAuthenticated, CallFormsHasPermission]
    permission_names = {
        "GET": "view_templateversion",
        "POST": "add_templateversion",
        "PUT": "change_templateversion",
        "PATCH": "change_templateversion",
        "DELETE": "delete_templateversion",
    }

    def get_serializer_class(self):
        if self.action in ["retrieve", "update", "partial_update"]:
            return TemplateVersionDetailSerializer
        return TemplateVersionSerializer

    def update(self, request, *args, **kwargs):
        version = self.get_object()
        if version.is_locked:
            return Response(
                {
                    "error": (
                        "This version has historical submissions and cannot be edited. "
                        "Use the clone action to create a new editable version instead."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def clone(self, request, pk=None):
        version = self.get_object()
        serializer = CloneVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            new_version = clone_template_version(
                source_version_or_id=version,
                created_by=request.user,
                new_label=data.get("version_label"),
                set_primary=data.get("set_primary", True),
            )
            return Response(
                TemplateVersionDetailSerializer(new_version).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["CallForms Templates"])
class TemplateFieldViewSet(viewsets.ModelViewSet):
    queryset = TemplateField.objects.all()
    serializer_class = TemplateFieldSerializer
    permission_classes = [IsAuthenticated, CallFormsHasPermission]
    permission_names = {
        "GET": "view_templatefield",
        "POST": "add_templatefield",
        "PUT": "change_templatefield",
        "PATCH": "change_templatefield",
        "DELETE": "delete_templatefield",
    }

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = serializer.validated_data["template_version"]

        if version.is_locked:
            return Response(
                {"error": "Cannot add fields to a locked template version."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        field = self.get_object()
        if field.template_version.is_locked:
            return Response(
                {"error": "Cannot edit fields on a locked template version."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        field = self.get_object()
        if field.template_version.is_locked:
            return Response(
                {"error": "Cannot delete fields from a locked template version."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        serializer = ReorderFieldsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            updated_fields = reorder_template_fields(
                version_or_id=data["template_version_id"],
                field_order_list=data["orders"],
            )
            return Response(
                TemplateFieldSerializer(updated_fields, many=True).data,
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["CallForms Templates"])
class PipelineStageActivityViewSet(viewsets.ModelViewSet):
    queryset = PipelineStageActivity.objects.all().select_related(
        "stage", "call_template"
    )
    permission_classes = [IsAuthenticated, CallFormsHasPermission]
    permission_names = {
        "GET": "view_pipelinestageactivity",
        "POST": "add_pipelinestageactivity",
        "PUT": "change_pipelinestageactivity",
        "PATCH": "change_pipelinestageactivity",
        "DELETE": "delete_pipelinestageactivity",
    }

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PipelineStageActivityDetailSerializer
        return PipelineStageActivitySerializer

    def perform_create(self, serializer):
        stage = serializer.validated_data["stage"]
        is_primary = serializer.validated_data.get("is_primary", False)
        if is_primary:
            stage.activities.update(is_primary=False)
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        is_primary = serializer.validated_data.get("is_primary", False)
        if is_primary and serializer.instance.stage:
            serializer.instance.stage.activities.exclude(
                pk=serializer.instance.pk
            ).update(is_primary=False)
        serializer.save()

    @action(detail=True, methods=["post"], url_path="set-primary")
    def set_primary_action(self, request, pk=None):
        activity = self.get_object()
        try:
            updated_activity = set_primary_stage_activity(activity.stage, activity)
            return Response(
                PipelineStageActivitySerializer(updated_activity).data,
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="for-stage")
    def for_stage_action(self, request):
        stage_id = request.query_params.get("stage_id")
        if not stage_id:
            return Response(
                {"error": "stage_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        activities = self.get_queryset().filter(stage_id=stage_id, is_active=True)
        return Response(PipelineStageActivitySerializer(activities, many=True).data)

    @action(detail=False, methods=["get"], url_path="lead-primary-form")
    def lead_primary_form_action(self, request):
        lead_id = request.query_params.get("lead_id")
        if not lead_id:
            return Response(
                {"error": "lead_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            form_data = get_lead_stage_primary_form(lead_id)
            return Response(form_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["CallForms Workflow"])
class CallAttemptViewSet(viewsets.ModelViewSet):
    queryset = CallAttempt.objects.all().select_related(
        "lead", "stage", "activity", "template_version", "agent"
    )
    serializer_class = CallAttemptSerializer
    permission_classes = [IsAuthenticated, CallFormsHasPermission]
    permission_names = {
        "GET": "view_callattempt",
        "POST": "add_callattempt",
        "PUT": "change_callattempt",
        "PATCH": "change_callattempt",
        "DELETE": "delete_callattempt",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        lead_id = self.request.query_params.get("lead_id")
        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        agent_id = self.request.query_params.get("agent_id")
        if agent_id:
            qs = qs.filter(agent_id=agent_id)
        outcome = self.request.query_params.get("outcome")
        if outcome:
            qs = qs.filter(outcome=outcome)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = LogCallAttemptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            attempt, suggest_mark_lost = log_call_attempt(
                lead_or_id=data["lead_id"],
                agent=request.user,
                stage_or_id=data.get("stage_id"),
                activity_or_id=data.get("activity_id"),
                template_version_or_id=data.get("template_version_id"),
                outcome=data.get("outcome"),
                notes=data.get("notes", ""),
                start_time=data.get("start_time"),
                end_time=data.get("end_time"),
            )
            response_data = CallAttemptSerializer(attempt).data
            response_data["suggest_mark_lost"] = suggest_mark_lost
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="lead-history")
    def lead_history_action(self, request):
        lead_id = request.query_params.get("lead_id")
        if not lead_id:
            return Response(
                {"error": "lead_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        attempts = (
            self.get_queryset().filter(lead_id=lead_id).order_by("attempt_number")
        )
        return Response(CallAttemptSerializer(attempts, many=True).data)


@extend_schema(tags=["CallForms Workflow"])
class FormSubmissionViewSet(viewsets.ModelViewSet):
    queryset = FormSubmission.objects.all().select_related(
        "lead", "call_attempt", "template_version", "submitted_by"
    )
    serializer_class = FormSubmissionSerializer
    permission_classes = [IsAuthenticated, CallFormsHasPermission]
    permission_names = {
        "GET": "view_formsubmission",
        "POST": "add_formsubmission",
        "PUT": "change_formsubmission",
        "PATCH": "change_formsubmission",
        "DELETE": "delete_formsubmission",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        lead_id = self.request.query_params.get("lead_id")
        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        version_id = self.request.query_params.get("template_version_id")
        if version_id:
            qs = qs.filter(template_version_id=version_id)

        field_key = self.request.query_params.get("field_key")
        field_value = self.request.query_params.get("field_value")
        if field_key and field_value is not None:
            qs = filter_submissions_by_field_value(qs, field_key, field_value)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = SubmitCallFormSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            submission = submit_call_form(
                lead_or_id=data["lead_id"],
                agent=request.user,
                template_version_or_id=data["template_version_id"],
                form_data=data["data"],
                call_attempt_or_id=data.get("call_attempt_id"),
                notes=data.get("notes", ""),
                quotation_or_id=data.get("quotation_id"),
            )
            return Response(
                FormSubmissionSerializer(submission).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="lead-timeline")
    def lead_timeline(self, request):
        """
        Consolidates CallAttempts and FormSubmissions into a single activity feed.
        Query params: ?lead_id=<uuid> OR ?account_id=<uuid> OR ?contact_id=<uuid>
        """
        lead_id = request.query_params.get("lead_id")
        account_id = request.query_params.get("account_id")
        contact_id = request.query_params.get("contact_id")

        if not lead_id and not account_id and not contact_id:
            return Response(
                {
                    "error": "At least one of lead_id, account_id, or contact_id query parameter is required"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            feed = get_lead_timeline_feed(
                lead_or_id=lead_id, account_id=account_id, contact_id=contact_id
            )
            return Response(feed, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="analytics")
    def analytics(self, request):
        """
        Aggregates submission metrics and field choice distributions for a TemplateVersion.
        Query param: ?template_version_id=<uuid>
        """
        version_id = request.query_params.get("template_version_id")
        if not version_id:
            return Response(
                {"error": "template_version_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = get_template_version_analytics(version_id)
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["CallForms Workflow"])
class TaskTriggerRuleViewSet(viewsets.ModelViewSet):
    queryset = TaskTriggerRule.objects.all().select_related(
        "template_version", "task_category", "task_priority", "specific_assignee"
    )
    serializer_class = TaskTriggerRuleSerializer
    permission_classes = [IsAuthenticated, CallFormsHasPermission]
    permission_names = {
        "GET": "view_tasktriggerrule",
        "POST": "add_tasktriggerrule",
        "PUT": "change_tasktriggerrule",
        "PATCH": "change_tasktriggerrule",
        "DELETE": "delete_tasktriggerrule",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        version_id = self.request.query_params.get("template_version_id")
        if version_id:
            qs = qs.filter(template_version_id=version_id)
        return qs


@extend_schema(tags=["CallForms Adhoc Proposals"])
class AdhocFieldProposalViewSet(viewsets.ModelViewSet):
    queryset = AdhocFieldProposal.objects.all().select_related(
        "template_version", "proposed_by", "reviewed_by"
    )
    serializer_class = AdhocFieldProposalSerializer
    permission_classes = [IsAuthenticated, CallFormsHasPermission]
    permission_names = {
        "GET": "view_adhocfieldproposal",
        "POST": "add_adhoc_field",
        "PUT": "manage_adhoc_field",
        "PATCH": "manage_adhoc_field",
        "DELETE": "manage_adhoc_field",
    }

    def perform_create(self, serializer):
        proposal = propose_adhoc_field(
            user=self.request.user,
            template_version=serializer.validated_data["template_version"],
            field_key=serializer.validated_data["field_key"],
            label=serializer.validated_data["label"],
            field_type=serializer.validated_data.get("field_type", "text"),
            help_text=serializer.validated_data.get("help_text"),
            options=serializer.validated_data.get("options"),
        )
        serializer.instance = proposal

    @extend_schema(
        summary="Review Ad-hoc Field Proposal",
        description="Manager reviews (approves or rejects) an agent ad-hoc field proposal.",
        request=ReviewAdhocFieldProposalSerializer,
        responses={200: AdhocFieldProposalSerializer},
    )
    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        proposal = self.get_object()
        serializer = ReviewAdhocFieldProposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_proposal = review_adhoc_field(
                user=request.user,
                proposal=proposal,
                status=serializer.validated_data["status"],
                rejection_reason=serializer.validated_data.get("rejection_reason"),
            )
            return Response(
                AdhocFieldProposalSerializer(updated_proposal).data,
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["CallForms Indexed Values"])
class IndexedSubmissionValueViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IndexedSubmissionValue.objects.all().select_related("submission")
    serializer_class = IndexedSubmissionValueSerializer
    permission_classes = [IsAuthenticated, CallFormsHasPermission]
    permission_names = {
        "GET": "view_indexedsubmissionvalue",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        submission_id = self.request.query_params.get("submission_id")
        field_key = self.request.query_params.get("field_key")
        if submission_id:
            qs = qs.filter(submission_id=submission_id)
        if field_key:
            qs = qs.filter(field_key=field_key)
        return qs
