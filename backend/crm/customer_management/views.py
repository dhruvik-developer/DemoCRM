import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

User = get_user_model()
logger = logging.getLogger(__name__)

from rest_framework import generics, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from audit_log.models import Activity, AuditLog

from .models import (
    Customer,
    CustomerAccount,
    CustomerContact,
    Lead,
    LeadSource,
    Payment,
    Pipeline,
    PipelineStage,
    Quotation,
    QuotationIntegrationEvent,
)
from .permissions import CRMHasPermission
from .serializers import (
    ActivitySerializer,
    AuditLogSerializer,
    CustomerAccountSerializer,
    CustomerContactSerializer,
    CustomerSerializer,
    LeadSerializer,
    LeadSourceSerializer,
    PaymentSerializer,
    PipelineSerializer,
    PipelineStageSerializer,
    QuotationIntegrationEventSerializer,
    QuotationSerializer,
)
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    inline_serializer,
)

from .services import CRMService, QuotationService
from .pdf_utils import generate_quotation_pdf


@extend_schema(tags=["Lead Sources"])
class LeadSourceListCreateView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_leadsource",
        "POST": "manage_lead_source",
    }

    @extend_schema(
        summary="List all lead sources",
        description="Retrieve a list of all lead sources. Requires view_leadsource permission.",
        operation_id="lead_source_list",
        responses={200: LeadSourceSerializer(many=True)},
    )
    def get(self, request):
        sources = LeadSource.objects.all()
        serializer = LeadSourceSerializer(sources, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create a lead source",
        description="Create a new lead source. Requires manage_lead_source permission.",
        operation_id="lead_source_create",
        request=LeadSourceSerializer,
        responses={
            201: LeadSourceSerializer,
            400: inline_serializer(
                "LeadSourceErrorResponse", fields={"detail": serializers.CharField()}
            ),
        },
    )
    def post(self, request):
        serializer = LeadSourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            source = CRMService.create_lead_source(
                user=request.user,
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get("description"),
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            LeadSourceSerializer(source).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Pipelines"])
class PipelineListCreateView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_pipeline",
        "POST": "manage_pipeline",
    }

    @extend_schema(
        summary="List all pipelines",
        description="Retrieve a list of all pipelines. Requires view_pipeline permission.",
        operation_id="pipeline_list",
        responses={200: PipelineSerializer(many=True)},
    )
    def get(self, request):
        pipelines = Pipeline.objects.all()
        serializer = PipelineSerializer(pipelines, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create a pipeline",
        description="Create a new pipeline. Requires manage_pipeline permission. Optionally clone stage skeleton from another pipeline (forms are NOT copied — each pipeline keeps isolated form links).",
        operation_id="pipeline_create",
        request=PipelineSerializer,
        responses={
            201: PipelineSerializer,
            400: inline_serializer(
                "PipelineErrorResponse", fields={"detail": serializers.CharField()}
            ),
        },
    )
    def post(self, request):
        serializer = PipelineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Optional: clone stage structure from an existing pipeline without copying forms.
        # Accept `clone_from_pipeline` or `clone_from` (UUID string). If not supplied
        # but other pipelines exist, service will clone from the most recent pipeline's
        # stage skeleton automatically when `auto_clone_stages` is truthy (default True
        # for UI convenience — preserves user's request: fresh pipeline with empty stages
        # copied from other pipeline but forms isolated).
        clone_from_id = (
            request.data.get("clone_from_pipeline")
            or request.data.get("clone_from")
            or request.data.get("copy_from_pipeline")
        )
        clone_from_pipeline = None
        if clone_from_id:
            try:
                clone_from_pipeline = Pipeline.objects.get(pk=clone_from_id)
            except Exception:
                return Response(
                    {"detail": "clone_from_pipeline not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Allow explicit opt-out via `clone_stages: false`
        clone_stages = request.data.get("clone_stages")
        if isinstance(clone_stages, str):
            clone_stages = clone_stages.lower() not in ("false", "0", "no")
        if clone_stages is None:
            clone_stages = True

        try:
            try:
                pipeline = CRMService.create_pipeline(
                    user=request.user,
                    name=serializer.validated_data["name"],
                    description=serializer.validated_data.get("description"),
                    clone_from_pipeline=clone_from_pipeline,
                    clone_stages=clone_stages,
                )
            except TypeError:
                # Container still running old code without clone_* args (volume not reloaded) — fallback
                pipeline = CRMService.create_pipeline(
                    user=request.user,
                    name=serializer.validated_data["name"],
                    description=serializer.validated_data.get("description"),
                )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            PipelineSerializer(pipeline).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Pipelines"])
class PipelineStageListCreateView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_pipelinestage",
        "POST": "manage_pipeline_stage",
    }

    @extend_schema(
        summary="List all pipeline stages",
        description="Retrieve a list of all pipeline stages. Requires view_pipelinestage permission.",
        operation_id="pipeline_stage_list",
        responses={200: PipelineStageSerializer(many=True)},
    )
    def get(self, request):
        pipeline_id = request.query_params.get("pipeline")
        stages = PipelineStage.objects.all()
        if pipeline_id:
            stages = stages.filter(pipeline_id=pipeline_id)
        stages = stages.order_by("pipeline__name", "display_order")
        serializer = PipelineStageSerializer(stages, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create a pipeline stage",
        description="Create a new pipeline stage. Requires manage_pipeline_stage permission.",
        operation_id="pipeline_stage_create",
        request=PipelineStageSerializer,
        responses={
            201: PipelineStageSerializer,
            400: inline_serializer(
                "PipelineStageErrorResponse", fields={"detail": serializers.CharField()}
            ),
        },
    )
    def post(self, request):
        serializer = PipelineStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage = CRMService.create_pipeline_stage(
                user=request.user,
                pipeline=serializer.validated_data["pipeline"],
                name=serializer.validated_data["name"],
                display_order=serializer.validated_data["display_order"],
                description=serializer.validated_data.get("description"),
                requires_quotation=serializer.validated_data.get(
                    "requires_quotation", False
                ),
                quotation_approval_required=serializer.validated_data.get(
                    "quotation_approval_required", False
                ),
            )
        except DjangoValidationError as exc:
            detail = exc.message if hasattr(exc, "message") else str(exc)
            # DRF ValidationError can carry dict
            if hasattr(exc, "message_dict"):
                detail = str(exc.message_dict)
            return Response(
                {"detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            PipelineStageSerializer(stage).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Lead Sources"])
class LeadSourceDetailView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "view_leadsource",
        "PATCH": "manage_lead_source",
        "PUT": "manage_lead_source",
        "DELETE": "manage_lead_source",
    }

    def get(self, request, pk):
        source = get_object_or_404(LeadSource, pk=pk)
        return Response(LeadSourceSerializer(source).data)

    def patch(self, request, pk):
        source = get_object_or_404(LeadSource, pk=pk)
        serializer = LeadSourceSerializer(source, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        source = get_object_or_404(LeadSource, pk=pk)
        source.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Pipelines"])
class PipelineDetailView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "view_pipeline",
        "PATCH": "manage_pipeline",
        "PUT": "manage_pipeline",
        "DELETE": "manage_pipeline",
    }

    def get(self, request, pk):
        pipeline = get_object_or_404(Pipeline, pk=pk)
        return Response(PipelineSerializer(pipeline).data)

    def patch(self, request, pk):
        pipeline = get_object_or_404(Pipeline, pk=pk)
        serializer = PipelineSerializer(pipeline, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        pipeline = get_object_or_404(Pipeline, pk=pk)
        # Isolated delete: remove only this pipeline's stage activities + stages, never touch other pipelines.
        from django.db import transaction
        from CallForms.models import PipelineStageActivity

        with transaction.atomic():
            stage_ids = list(pipeline.stages.values_list("id", flat=True))
            if stage_ids:
                PipelineStageActivity.objects.filter(stage_id__in=stage_ids).delete()
                pipeline.stages.all().delete()
            pipeline.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Pipelines"])
class PipelineStageDetailView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "view_pipelinestage",
        "PATCH": "manage_pipeline_stage",
        "PUT": "manage_pipeline_stage",
        "DELETE": "manage_pipeline_stage",
    }

    def get(self, request, pk):
        stage = get_object_or_404(PipelineStage, pk=pk)
        return Response(PipelineStageSerializer(stage).data)

    def patch(self, request, pk):
        stage = get_object_or_404(PipelineStage, pk=pk)
        serializer = PipelineStageSerializer(stage, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        stage = get_object_or_404(PipelineStage, pk=pk)
        stage.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Leads"])
class LeadListCreateView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_lead",
        "POST": "add_lead",
    }

    @extend_schema(
        summary="List all leads",
        description="Retrieve a list of all leads. Requires view_lead permission.",
        operation_id="lead_list",
        responses={200: LeadSerializer(many=True)},
    )
    def get(self, request):
        leads = Lead.objects.select_related(
            "source",
            "assigned_to",
            "pipeline",
            "current_stage",
        ).all()

        serializer = LeadSerializer(
            leads,
            many=True,
        )

        return Response(serializer.data)

    @extend_schema(
        summary="Create a new lead",
        description="Create a new lead. Requires add_lead permission.",
        operation_id="lead_create",
        request=LeadSerializer,
        responses={
            201: LeadSerializer,
            400: inline_serializer(
                "LeadCreateErrorResponse", fields={"detail": serializers.CharField()}
            ),
        },
    )
    def post(self, request):
        serializer = LeadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            lead = CRMService.create_lead(
                user=request.user,
                name=serializer.validated_data["name"],
                email=serializer.validated_data.get("email"),
                phone=serializer.validated_data.get("phone"),
                company_name=serializer.validated_data.get("company_name"),
                source=serializer.validated_data["source"],
                assigned_to=serializer.validated_data["assigned_to"],
                pipeline=serializer.validated_data["pipeline"],
                current_stage=serializer.validated_data["current_stage"],
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            LeadSerializer(lead).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Leads"])
class LeadDetailView(generics.RetrieveUpdateAPIView):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_lead",
        "PUT": "change_lead",
        "PATCH": "change_lead",
    }

    @extend_schema(
        summary="Retrieve a lead by UUID",
        description="Retrieve detailed information about a lead. Requires view_lead permission.",
        operation_id="lead_retrieve",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Lead UUID"),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update a lead",
        description="Update a lead. Requires change_lead permission.",
        operation_id="lead_update",
        request=LeadSerializer,
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Lead UUID"),
        ],
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a lead",
        description="Partially update a lead. Requires change_lead permission.",
        operation_id="lead_partial_update",
        request=LeadSerializer,
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Lead UUID"),
        ],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def perform_update(self, serializer):
        old_lead = self.get_object()
        old_data = {
            "name": old_lead.name,
            "email": old_lead.email,
            "phone": old_lead.phone,
            "company_name": old_lead.company_name,
        }

        updated_lead = serializer.save()

        new_data = {
            "name": updated_lead.name,
            "email": updated_lead.email,
            "phone": updated_lead.phone,
            "company_name": updated_lead.company_name,
        }

        CRMService.create_audit_log(
            user=self.request.user,
            entity_type="Lead",
            entity_id=updated_lead.id,
            action="LEAD_UPDATED",
            old_value=old_data,
            new_value=new_data,
        )


@extend_schema(tags=["Leads"])
class LeadAssignView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "assign_lead",
    }

    @extend_schema(
        summary="Assign a lead to a user",
        description="Assign a lead to a user. Requires assign_lead permission.",
        operation_id="lead_assign",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Lead UUID"),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "assigned_to": {
                        "type": "integer",
                        "description": "User ID to assign the lead to",
                    },
                },
                "required": ["assigned_to"],
            }
        },
        responses={
            200: LeadSerializer,
            400: inline_serializer(
                "LeadAssignErrorResponse", fields={"detail": serializers.CharField()}
            ),
            404: inline_serializer(
                "LeadAssignNotFoundResponse", fields={"detail": serializers.CharField()}
            ),
        },
    )
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)

        assigned_to_id = request.data.get("assigned_to")

        if not assigned_to_id:
            return Response(
                {"assigned_to": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_assignee = get_object_or_404(
            User,
            pk=assigned_to_id,
        )

        try:
            lead = CRMService.assign_lead(
                user=request.user,
                lead=lead,
                new_assignee=new_assignee,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            LeadSerializer(lead).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Leads"])
class LeadProgressView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "progress_lead",
    }

    @extend_schema(
        summary="Progress a lead to next pipeline stage",
        description="Progress a lead to the next pipeline stage. Requires progress_lead permission.",
        operation_id="lead_progress",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Lead UUID"),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "stage_id": {
                        "type": "integer",
                        "description": "Pipeline stage ID to progress to",
                    },
                },
                "required": ["stage_id"],
            }
        },
        responses={
            200: LeadSerializer,
            400: inline_serializer(
                "LeadProgressErrorResponse", fields={"detail": serializers.CharField()}
            ),
        },
    )
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)

        stage_id = request.data.get("stage_id")

        try:
            lead = CRMService.progress_lead(
                user=request.user,
                lead=lead,
                stage_id=stage_id,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            LeadSerializer(lead).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Leads"])
class LeadLostView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "mark_lead_lost",
    }

    @extend_schema(
        summary="Mark a lead as lost",
        description="Mark a lead as lost with a reason. Requires mark_lead_lost permission.",
        operation_id="lead_lost",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Lead UUID"),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "lost_reason": {
                        "type": "string",
                        "description": "Reason for losing the lead",
                    },
                },
                "required": ["lost_reason"],
            }
        },
        responses={
            200: LeadSerializer,
            400: inline_serializer(
                "LeadLostErrorResponse", fields={"detail": serializers.CharField()}
            ),
        },
    )
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)

        lost_reason = request.data.get("lost_reason")

        if not lost_reason:
            return Response(
                {"lost_reason": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lead = CRMService.mark_lead_lost(
                user=request.user,
                lead=lead,
                lost_reason=lost_reason,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            LeadSerializer(lead).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Leads"])
class LeadReengageView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "reengage_lead",
    }

    @extend_schema(
        summary="Re-engage a lost lead",
        description="Re-engage a lost lead back into the pipeline. Requires reengage_lead permission.",
        operation_id="lead_reengage",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Lead UUID"),
        ],
        request=None,
        responses={
            200: LeadSerializer,
            400: inline_serializer(
                "LeadReengageErrorResponse", fields={"detail": serializers.CharField()}
            ),
        },
    )
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)

        try:
            lead = CRMService.reengage_lead(
                user=request.user,
                lead=lead,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            LeadSerializer(lead).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Leads"])
class LeadConvertView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "convert_lead",
    }

    @extend_schema(
        summary="Convert a lead to customer",
        description="Convert a lead to a customer. Requires convert_lead permission.",
        operation_id="lead_convert",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Lead UUID"),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Customer name (defaults to lead name)",
                    },
                    "email": {
                        "type": "string",
                        "description": "Customer email (defaults to lead email)",
                    },
                    "phone": {
                        "type": "string",
                        "description": "Customer phone (defaults to lead phone)",
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Company name (defaults to lead company)",
                    },
                },
            }
        },
        responses={
            201: CustomerSerializer,
            400: inline_serializer(
                "LeadConvertErrorResponse", fields={"detail": serializers.CharField()}
            ),
        },
    )
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)

        name = request.data.get("name", lead.name)
        email = request.data.get("email", lead.email)
        phone = request.data.get("phone", lead.phone)
        company_name = request.data.get(
            "company_name",
            lead.company_name,
        )
        gst_number = request.data.get("gst_number")

        if not email:
            return Response(
                {"email": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not phone:
            return Response(
                {"phone": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            customer = CRMService.convert_lead(
                user=request.user,
                lead=lead,
                name=name,
                email=email,
                phone=phone,
                company_name=company_name,
                gst_number=gst_number,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            CustomerSerializer(customer).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Activities"])
class ActivityListCreateView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_activity",
        "POST": "add_activity",
    }

    @extend_schema(
        summary="List all activities",
        description="Retrieve a list of all activities. Requires view_activity permission.",
        operation_id="activity_list",
        responses={200: ActivitySerializer(many=True)},
    )
    def get(self, request):
        lead_id = request.query_params.get("lead")
        customer_id = request.query_params.get("customer")
        activities = Activity.objects.select_related(
            "lead",
            "customer",
            "created_by",
        ).order_by("-created_at")

        # Lead-scoped feed: only show rows related to this lead, otherwise page becomes long global logs
        if lead_id:
            activities = activities.filter(lead_id=lead_id)
        if customer_id:
            activities = activities.filter(customer_id=customer_id)

        serializer = ActivitySerializer(
            activities,
            many=True,
        )

        return Response(serializer.data)

    @extend_schema(
        summary="Create an activity",
        description="Create a new activity. Requires add_activity permission.",
        operation_id="activity_create",
        request=ActivitySerializer,
        responses={
            201: ActivitySerializer,
            400: inline_serializer(
                "ActivityErrorResponse", fields={"detail": serializers.CharField()}
            ),
        },
    )
    def post(self, request):
        serializer = ActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            activity = CRMService.create_activity(
                user=request.user,
                activity_type=serializer.validated_data["activity_type"],
                outcome=serializer.validated_data["outcome"],
                lead=serializer.validated_data.get("lead"),
                customer=serializer.validated_data.get("customer"),
                notes=serializer.validated_data.get("notes"),
                follow_up_required=serializer.validated_data.get(
                    "follow_up_required",
                    False,
                ),
                follow_up_date=serializer.validated_data.get("follow_up_date"),
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            ActivitySerializer(activity).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Audit Logs"])
class AuditLogListView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_auditlog",
    }

    @extend_schema(
        summary="List all audit logs",
        description="Retrieve a list of all audit logs. Requires view_auditlog permission.",
        operation_id="audit_log_list",
        responses={200: AuditLogSerializer(many=True)},
    )
    def get(self, request):
        logs = AuditLog.objects.select_related("user").order_by("-created_at")

        # Pagination: ?page=1&page_size=20 (default 20, max 100) — avoids infinite scroll on long pages
        from django.core.paginator import EmptyPage, Paginator

        try:
            page = int(request.query_params.get("page", "1"))
        except ValueError:
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", "20"))
        except ValueError:
            page_size = 20
        page_size = max(1, min(page_size, 100))
        paginator = Paginator(logs, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = (
                paginator.page(paginator.num_pages) if paginator.num_pages else []
            )

        serializer = AuditLogSerializer(
            page_obj.object_list if hasattr(page_obj, "object_list") else [],
            many=True,
        )

        return Response(
            {
                "count": paginator.count,
                "num_pages": paginator.num_pages,
                "page": page,
                "page_size": page_size,
                "results": serializer.data,
            }
        )


@extend_schema(tags=["Customers"])
class CustomerListCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_customer",
        "POST": "add_customer",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            from django.db.models import Q

            qs = qs.filter(
                Q(name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
                | Q(company_name__icontains=search)
            )
        return qs

    @extend_schema(
        summary="List all customers",
        description="Retrieve a list of all customers. Requires view_customer permission.",
        operation_id="customer_list",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create a customer",
        description="Create a new customer. Requires add_customer permission.",
        operation_id="customer_create",
        request=CustomerSerializer,
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        lead = serializer.validated_data.get("lead")
        if not lead:
            from rest_framework.exceptions import ValidationError as DRFValidationError

            raise DRFValidationError(
                {"lead": "A lead is required to create a customer."}
            )

        if lead.status != Lead.Status.CONVERTED:
            from rest_framework.exceptions import ValidationError as DRFValidationError

            raise DRFValidationError(
                {"lead": "Customer can only be created from a CONVERTED Lead."}
            )

        customer = serializer.save()

        CRMService.create_audit_log(
            user=self.request.user,
            entity_type="Customer",
            entity_id=customer.id,
            action="CUSTOMER_CREATED",
            new_value={
                "lead": str(customer.lead_id),
                "name": customer.name,
                "email": customer.email,
            },
        )


@extend_schema(tags=["Customers"])
class CustomerDetailView(generics.RetrieveAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_customer",
    }

    @extend_schema(
        summary="Retrieve a customer by UUID",
        description="Retrieve detailed information about a customer. Requires view_customer permission.",
        operation_id="customer_retrieve",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Customer UUID"),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(tags=["Customers"])
class CustomerActivityListView(generics.ListAPIView):
    serializer_class = ActivitySerializer
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_activity",
    }

    @extend_schema(
        summary="List activities for a customer",
        description="Retrieve all activities associated with a customer. Requires view_activity permission.",
        operation_id="customer_activity_list",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Customer UUID"),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        customer_id = self.kwargs["pk"]

        return (
            Activity.objects.filter(customer_id=customer_id)
            .select_related("customer", "created_by")
            .order_by("-created_at")
        )


# ==============================================================================
# QUOTATION WORKFLOW VIEWS (MEMBER 2)
# ==============================================================================


@extend_schema(tags=["Quotations"])
class QuotationListCreateView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "view_quotation",
        "POST": "add_quotation",
    }

    @extend_schema(
        summary="List all quotations",
        description="Retrieve a list of all quotations. Requires view_quotation permission.",
        operation_id="quotation_list",
        parameters=[
            OpenApiParameter(
                name="lead",
                type=str,
                description="Filter quotations by lead UUID",
                required=False,
            ),
        ],
        responses={200: QuotationSerializer(many=True)},
    )
    def get(self, request):
        lead_id = request.query_params.get("lead")
        queryset = Quotation.objects.select_related(
            "lead",
            "customer",
            "created_by",
            "current_version",
            "current_version__created_by",
            "current_version__assigned_to",
            "current_version__pipeline",
            "current_version__current_stage",
        ).prefetch_related(
            "current_version__line_items",
            "current_version__approvals",
            "versions",
            "versions__line_items",
            "versions__approvals",
        )

        if lead_id:
            queryset = queryset.filter(lead_id=lead_id)

        serializer = QuotationSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create a quotation with line items",
        description="Create a new quotation with optional line items. Requires add_quotation permission.",
        operation_id="quotation_create",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "lead_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Lead UUID (required)",
                    },
                    "terms": {"type": "string", "description": "Quotation terms"},
                    "notes": {"type": "string", "description": "Quotation notes"},
                    "line_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit_price": {"type": "number"},
                            },
                        },
                        "description": "Line items for the quotation",
                    },
                },
                "required": ["lead_id"],
            }
        },
        responses={
            201: QuotationSerializer,
            400: inline_serializer(
                "QuotationCreateErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        lead_id = request.data.get("lead_id") or request.data.get("lead")
        if not lead_id:
            return Response(
                {"lead_id": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lead = get_object_or_404(Lead, pk=lead_id)
        terms = request.data.get("terms")
        notes = request.data.get("notes")
        line_items = request.data.get("line_items")
        if line_items is None:
            line_items = request.data.get("items")
        discount_type = request.data.get("discount_type")
        discount_value = request.data.get("discount_value")
        gst_rate = request.data.get("gst_rate")

        try:
            quotation = QuotationService.create_quotation(
                user=request.user,
                lead=lead,
                terms=terms,
                notes=notes,
                line_items=line_items,
                discount_type=discount_type,
                discount_value=discount_value,
                gst_rate=gst_rate,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            QuotationSerializer(quotation).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Quotations"])
class QuotationDetailView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "view_quotation",
        "DELETE": "delete_quotation",
    }

    @extend_schema(
        summary="Retrieve quotation detail",
        description="Retrieve detailed information about a quotation. Requires view_quotation permission.",
        operation_id="quotation_retrieve",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Quotation UUID"),
        ],
        responses={
            200: QuotationSerializer,
            404: inline_serializer(
                "QuotationDetailNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def get(self, request, pk):
        quotation = get_object_or_404(
            Quotation.objects.select_related(
                "lead", "customer", "created_by", "current_version"
            ).prefetch_related(
                "versions", "versions__line_items", "versions__approvals"
            ),
            pk=pk,
        )
        serializer = QuotationSerializer(quotation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Delete a draft quotation",
        description="Delete a draft quotation. Only DRAFT quotations can be deleted; sent/accepted/rejected quotations are preserved for audit. Requires delete_quotation permission or ownership.",
        operation_id="quotation_delete",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Quotation UUID"),
        ],
        responses={
            204: None,
            400: inline_serializer(
                "QuotationDeleteErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
            404: inline_serializer(
                "QuotationDeleteNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def delete(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        # Only DRAFT can be deleted — preserve audit trail for sent/accepted
        if quotation.status != "DRAFT" or (
            quotation.current_version and quotation.current_version.status != "DRAFT"
        ):
            return Response(
                {
                    "detail": "Only draft quotations can be deleted. Sent/accepted quotations are preserved for audit."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Check delete permission via role (has_perm does not check role)
        role = getattr(request.user, "role", None)
        has_delete = (
            role and role.permissions.filter(codename="delete_quotation").exists()
        )
        has_change = (
            role and role.permissions.filter(codename="change_quotation").exists()
        )
        is_owner = quotation.created_by_id == request.user.user_id
        if not is_owner and not request.user.is_superuser and not has_delete:
            # Fallback: allow if user has change_quotation (draft editor)
            if not has_change:
                return Response(
                    {
                        "detail": "You do not have permission to delete this quotation. Ask admin to grant 'delete_quotation' in Roles & permissions → Employee → Save."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        qnum = quotation.quotation_number
        # Unlink protected Activity.quotation (PROTECT) so draft can be deleted — keep lead/customer history
        try:
            from audit_log.models import Activity

            Activity.objects.filter(quotation=quotation).update(quotation=None)
        except Exception:
            pass
        quotation.delete()
        # Audit
        try:
            from crm.services import CRMService

            CRMService.create_audit_log(
                user=request.user,
                entity_type="Quotation",
                entity_id=pk,
                action="QUOTATION_DELETED",
                metadata={"quotation_number": qnum},
            )
        except Exception:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Quotations"])
class QuotationUpdateDraftView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "PATCH": "change_quotation",
        "PUT": "change_quotation",
    }

    @extend_schema(
        summary="Update a draft quotation",
        description="Update a draft quotation's terms, notes, or line items. Requires change_quotation permission.",
        operation_id="quotation_update_draft",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Quotation UUID"),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "terms": {"type": "string", "description": "Quotation terms"},
                    "notes": {"type": "string", "description": "Quotation notes"},
                    "line_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit_price": {"type": "number"},
                            },
                        },
                        "description": "Line items for the quotation",
                    },
                },
            }
        },
        responses={
            200: QuotationSerializer,
            400: inline_serializer(
                "QuotationUpdateDraftErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def patch(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        terms = request.data.get("terms")
        notes = request.data.get("notes")
        line_items = request.data.get("line_items")
        discount_type = request.data.get("discount_type")
        discount_value = request.data.get("discount_value")
        gst_rate = request.data.get("gst_rate")

        try:
            quotation = QuotationService.update_draft_quotation(
                user=request.user,
                quotation=quotation,
                terms=terms,
                notes=notes,
                line_items=line_items,
                discount_type=discount_type,
                discount_value=discount_value,
                gst_rate=gst_rate,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            QuotationSerializer(quotation).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Quotations"])
class QuotationSubmitView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "submit_quotation",
    }

    @extend_schema(
        summary="Submit quotation for approval",
        description="Submit a quotation for approval. Requires submit_quotation permission.",
        operation_id="quotation_submit",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Quotation UUID"),
        ],
        request=None,
        responses={
            200: QuotationSerializer,
            400: inline_serializer(
                "QuotationSubmitErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)

        try:
            quotation = QuotationService.submit_quotation_for_approval(
                user=request.user,
                quotation=quotation,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            QuotationSerializer(quotation).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Quotations"])
class QuotationApproveView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "approve_quotation",
    }

    @extend_schema(
        summary="Approve a quotation",
        description="Approve a quotation. Requires approve_quotation permission.",
        operation_id="quotation_approve",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Quotation UUID"),
        ],
        request=None,
        responses={
            200: QuotationSerializer,
            400: inline_serializer(
                "QuotationApproveErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
            403: inline_serializer(
                "QuotationApproveForbiddenResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)

        try:
            quotation = QuotationService.approve_quotation(
                reviewer_user=request.user,
                quotation=quotation,
            )
        except PermissionDenied as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            QuotationSerializer(quotation).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Quotations"])
class QuotationRejectApprovalView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "approve_quotation",
    }

    @extend_schema(
        summary="Reject quotation approval",
        description="Reject a quotation's approval. Requires approve_quotation permission.",
        operation_id="quotation_reject_approval",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Quotation UUID"),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for rejecting approval",
                    },
                },
            }
        },
        responses={
            200: QuotationSerializer,
            400: inline_serializer(
                "QuotationRejectApprovalErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        reason = request.data.get("reason")

        try:
            quotation = QuotationService.reject_quotation_approval(
                reviewer_user=request.user,
                quotation=quotation,
                reason=reason,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            QuotationSerializer(quotation).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Quotations"])
class QuotationSendView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "send_quotation",
    }

    @extend_schema(
        summary="Mark quotation as sent",
        description="Mark a quotation as sent. Requires send_quotation permission.",
        operation_id="quotation_send",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Quotation UUID"),
        ],
        request=None,
        responses={
            200: QuotationSerializer,
            400: inline_serializer(
                "QuotationSendErrorResponse", fields={"detail": serializers.CharField()}
            ),
        },
    )
    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)

        try:
            quotation = QuotationService.send_quotation(
                user=request.user,
                quotation=quotation,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            QuotationSerializer(quotation).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Quotations"])
class QuotationRevisionView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "request_quotation_revision",
    }

    @extend_schema(
        summary="Request quotation revision",
        description="Request a revision to a quotation. Requires request_quotation_revision permission.",
        operation_id="quotation_revision",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Quotation UUID"),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "terms": {"type": "string", "description": "Updated terms"},
                    "notes": {"type": "string", "description": "Updated notes"},
                    "line_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit_price": {"type": "number"},
                            },
                        },
                        "description": "Updated line items",
                    },
                    "revision_reason": {
                        "type": "string",
                        "description": "Reason for the revision",
                    },
                },
            }
        },
        responses={
            201: QuotationSerializer,
            400: inline_serializer(
                "QuotationRevisionErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        terms = request.data.get("terms")
        notes = request.data.get("notes")
        line_items = request.data.get("line_items")
        revision_reason = request.data.get("revision_reason") or request.data.get(
            "reason"
        )
        discount_type = request.data.get("discount_type")
        discount_value = request.data.get("discount_value")
        gst_rate = request.data.get("gst_rate")

        try:
            quotation = QuotationService.create_revision(
                user=request.user,
                quotation=quotation,
                terms=terms,
                notes=notes,
                line_items=line_items,
                revision_reason=revision_reason,
                discount_type=discount_type,
                discount_value=discount_value,
                gst_rate=gst_rate,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            QuotationSerializer(quotation).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Quotations"])
class QuotationAcceptView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "accept_quotation",
    }

    @extend_schema(
        summary="Accept a quotation (creates customer)",
        description="Accept a quotation and create a customer. Requires accept_quotation permission.",
        operation_id="quotation_accept",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Quotation UUID"),
        ],
        request=None,
        responses={
            200: inline_serializer(
                "QuotationAcceptSuccessResponse",
                fields={
                    "quotation": QuotationSerializer(),
                    "customer": CustomerSerializer(allow_null=True),
                },
            ),
            400: inline_serializer(
                "QuotationAcceptErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)

        try:
            quotation, customer = QuotationService.accept_quotation(
                user=request.user,
                quotation=quotation,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "quotation": QuotationSerializer(quotation).data,
                "customer": CustomerSerializer(customer).data if customer else None,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Quotations"])
class QuotationRejectView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "reject_quotation",
    }

    @extend_schema(
        summary="Reject a quotation",
        description="Reject a quotation with a reason. Requires reject_quotation permission.",
        operation_id="quotation_reject",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Quotation UUID"),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "rejection_reason": {
                        "type": "string",
                        "description": "Reason for rejecting the quotation",
                    },
                },
                "required": ["rejection_reason"],
            }
        },
        responses={
            200: QuotationSerializer,
            400: inline_serializer(
                "QuotationRejectErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        rejection_reason = request.data.get("rejection_reason") or request.data.get(
            "reason"
        )

        if not rejection_reason:
            return Response(
                {"rejection_reason": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quotation = QuotationService.reject_quotation(
                user=request.user,
                quotation=quotation,
                rejection_reason=rejection_reason,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            QuotationSerializer(quotation).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Quotations"])
class QuotationIntegrationEventListView(generics.ListAPIView):
    queryset = QuotationIntegrationEvent.objects.all()
    serializer_class = QuotationIntegrationEventSerializer
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "view_quotation",
    }

    @extend_schema(
        summary="List quotation integration events",
        description="Retrieve a list of all quotation integration events. Requires view_quotation permission.",
        operation_id="quotation_event_list",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(tags=["Quotations"])
class QuotationPDFView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "generate_quotation_pdf",
    }

    @extend_schema(
        summary="Generate and download quotation PDF",
        description="Generate and download a PDF for a quotation. Requires generate_quotation_pdf permission.",
        operation_id="quotation_pdf_download",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Quotation UUID"),
            OpenApiParameter(
                name="version",
                type=int,
                description="Quotation version number (optional)",
                required=False,
            ),
        ],
        responses={
            (200, "application/pdf"): OpenApiResponse(
                response=bytes, description="Quotation PDF file"
            ),
            400: inline_serializer(
                "QuotationPdfErrorResponse", fields={"detail": serializers.CharField()}
            ),
            404: inline_serializer(
                "QuotationPdfNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
            500: inline_serializer(
                "QuotationPdfServerErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def get(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)

        version_param = request.query_params.get("version")
        if version_param is not None:
            try:
                v_num = int(version_param)
                version = quotation.versions.filter(version_number=v_num).first()
                if not version:
                    return Response(
                        {"detail": f"Quotation version {v_num} not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            except ValueError:
                return Response(
                    {"detail": "Invalid version parameter."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            version = quotation.current_version

        if not version:
            return Response(
                {"detail": "Quotation has no active version."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if version.status in ["DRAFT", "PENDING_APPROVAL"]:
            return Response(
                {
                    "detail": f"PDF download is not allowed for quotations in state '{version.status}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pdf_bytes = generate_quotation_pdf(version)
        except Exception as exc:
            logger.error("Failed to generate quotation PDF: %s", str(exc))
            return Response(
                {"detail": f"Failed to generate PDF: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        CRMService.create_audit_log(
            user=request.user,
            entity_type="Quotation",
            entity_id=quotation.id,
            action="QUOTATION_PDF_GENERATED",
            metadata={
                "version": version.version_number,
                "quotation_number": quotation.quotation_number,
            },
        )

        filename = f"{quotation.quotation_number}_v{version.version_number}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


@extend_schema(tags=["Quotations"])
class QuotationSendEmailView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "send_quotation",
    }

    @extend_schema(
        summary="Send quotation via email",
        description="Send a quotation via email. Requires send_quotation permission.",
        operation_id="quotation_send_email",
        parameters=[
            OpenApiParameter(name="pk", type=str, description="Quotation UUID"),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "recipient_email": {
                        "type": "string",
                        "description": "Recipient email address",
                    },
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body"},
                    "version": {
                        "type": "integer",
                        "description": "Quotation version number (optional)",
                    },
                },
            }
        },
        responses={
            200: inline_serializer(
                "QuotationSendEmailSuccessResponse",
                fields={
                    "detail": serializers.CharField(),
                    "quotation": QuotationSerializer(),
                },
            ),
            400: inline_serializer(
                "QuotationSendEmailErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)

        recipient_email = request.data.get("recipient_email")
        subject = request.data.get("subject")
        body = request.data.get("body")
        version_param = request.data.get("version")

        version_number = None
        if version_param is not None:
            try:
                version_number = int(version_param)
            except (ValueError, TypeError):
                return Response(
                    {"detail": "Invalid version parameter."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            quotation, version = QuotationService.send_quotation_email(
                user=request.user,
                quotation=quotation,
                version_number=version_number,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": f"Quotation email sent to {version.sent_to}.",
                "quotation": QuotationSerializer(quotation).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Payments"])
class PaymentListView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {"GET": "view_payment"}

    @extend_schema(
        summary="List payments",
        description="List manual payment entries. Filter by ?lead=<uuid>&customer=<uuid>. Requires view_payment.",
        parameters=[
            OpenApiParameter(
                name="lead", type=str, required=False, description="Lead UUID"
            ),
            OpenApiParameter(
                name="customer", type=str, required=False, description="Customer UUID"
            ),
        ],
    )
    def get(self, request):
        qs = Payment.objects.select_related("lead", "customer", "created_by").all()
        lead_id = request.query_params.get("lead")
        customer_id = request.query_params.get("customer")
        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        serializer = PaymentSerializer(qs, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Payments"])
class LeadRecordPaymentView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {"POST": "record_payment"}

    @extend_schema(
        summary="Record payment for a lead",
        description="Manual payment entry — updates paid_amount/due_amount/financial_status. Requires record_payment. Amount must not exceed due.",
        parameters=[
            OpenApiParameter(
                name="pk",
                type=str,
                location=OpenApiParameter.PATH,
                description="Lead UUID",
            )
        ],
        request=inline_serializer(
            "LeadPaymentRequest",
            fields={
                "amount": serializers.DecimalField(max_digits=12, decimal_places=2),
                "payment_date": serializers.DateField(required=False),
                "method": serializers.CharField(required=False),
                "reference": serializers.CharField(required=False, allow_blank=True),
                "notes": serializers.CharField(required=False, allow_blank=True),
            },
        ),
    )
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        from decimal import Decimal

        amount = request.data.get("amount")
        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response(
                {"amount": ["Invalid amount."]}, status=status.HTTP_400_BAD_REQUEST
            )
        payment_date = request.data.get("payment_date")
        if payment_date:
            from django.utils.dateparse import parse_date

            try:
                payment_date = parse_date(str(payment_date))
            except Exception:
                payment_date = None
        method = request.data.get("method", "CASH")
        reference = request.data.get("reference")
        notes = request.data.get("notes")
        try:
            payment, updated_lead = CRMService.record_payment(
                user=request.user,
                lead=lead,
                amount=amount,
                payment_date=payment_date,
                method=method,
                reference=reference,
                notes=notes,
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "lead": LeadSerializer(updated_lead).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Payments"])
class CustomerRecordPaymentView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {"POST": "record_payment"}

    @extend_schema(
        summary="Record payment for a customer",
        description="Manual payment entry via customer. Resolved to its lead. Requires record_payment.",
        parameters=[
            OpenApiParameter(
                name="pk",
                type=str,
                location=OpenApiParameter.PATH,
                description="Customer UUID",
            )
        ],
        request=inline_serializer(
            "CustomerPaymentRequest",
            fields={
                "amount": serializers.DecimalField(max_digits=12, decimal_places=2),
                "payment_date": serializers.DateField(required=False),
                "method": serializers.CharField(required=False),
                "reference": serializers.CharField(required=False, allow_blank=True),
                "notes": serializers.CharField(required=False, allow_blank=True),
            },
        ),
    )
    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        from decimal import Decimal

        amount = request.data.get("amount")
        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response(
                {"amount": ["Invalid amount."]}, status=status.HTTP_400_BAD_REQUEST
            )
        payment_date = request.data.get("payment_date")
        if payment_date:
            from django.utils.dateparse import parse_date

            try:
                payment_date = parse_date(str(payment_date))
            except Exception:
                payment_date = None
        method = request.data.get("method", "CASH")
        reference = request.data.get("reference")
        notes = request.data.get("notes")
        try:
            payment, updated_lead = CRMService.record_payment(
                user=request.user,
                customer=customer,
                amount=amount,
                payment_date=payment_date,
                method=method,
                reference=reference,
                notes=notes,
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        # Refresh customer lead data via smart lookup? Return payment + lead
        lead_data = LeadSerializer(updated_lead).data if updated_lead else None
        return Response(
            {"payment": PaymentSerializer(payment).data, "lead": lead_data},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Customers"])
class SmartCustomerLookupView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "view_customer",
    }

    @extend_schema(
        summary="Smart Customer Lookup",
        description="Searches CustomerAccount and CustomerContact using multi-field matching (email, phone, gst_number, company_name) and returns unified multi-pipeline portfolio breakdown.",
        parameters=[
            OpenApiParameter(
                "query",
                str,
                description="Search term (name, email, phone, company, or GST)",
            ),
            OpenApiParameter("email", str, description="Customer email address"),
            OpenApiParameter("phone", str, description="Customer phone number"),
            OpenApiParameter("gst_number", str, description="B2B Company GST Tax ID"),
            OpenApiParameter("company_name", str, description="B2B Company Name"),
        ],
    )
    def get(self, request):
        query = request.query_params.get("query")
        email = request.query_params.get("email")
        phone = request.query_params.get("phone")
        gst_number = request.query_params.get("gst_number")
        company_name = request.query_params.get("company_name")

        res = CRMService.smart_customer_lookup(
            query=query,
            email=email,
            phone=phone,
            gst_number=gst_number,
            company_name=company_name,
        )
        return Response(res, status=status.HTTP_200_OK)


@extend_schema(tags=["Customers"])
class CustomerAccountListCreateView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "view_customeraccount",
        "POST": "manage_customer_account",
    }

    def get(self, request):
        qs = CustomerAccount.objects.all()
        serializer = CustomerAccountSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CustomerAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Customers"])
class CustomerContactListCreateView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "view_customercontact",
        "POST": "manage_customer_contact",
    }

    def get(self, request):
        qs = CustomerContact.objects.all()
        serializer = CustomerContactSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CustomerContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
