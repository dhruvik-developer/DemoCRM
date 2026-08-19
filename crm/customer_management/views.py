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

from .models import (
    Activity,
    AuditLog,
    Customer,
    Lead,
    LeadSource,
    Pipeline,
    PipelineStage,
    Quotation,
    QuotationIntegrationEvent,
)
from .permissions import CRMHasPermission
from .serializers import (
    ActivitySerializer,
    AuditLogSerializer,
    CustomerSerializer,
    LeadSerializer,
    LeadSourceSerializer,
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
        description="Create a new pipeline. Requires manage_pipeline permission.",
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

        try:
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
        stages = PipelineStage.objects.all()
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
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            PipelineStageSerializer(stage).data,
            status=status.HTTP_201_CREATED,
        )


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
        activities = Activity.objects.select_related(
            "lead",
            "customer",
            "created_by",
        ).all()

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
        logs = AuditLog.objects.select_related("user").all()

        serializer = AuditLogSerializer(
            logs,
            many=True,
        )

        return Response(serializer.data)


@extend_schema(tags=["Customers"])
class CustomerListCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_customer",
        "POST": "add_customer",
    }

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
            line_items = request.data.get("items", [])

        try:
            quotation = QuotationService.create_quotation(
                user=request.user,
                lead=lead,
                terms=terms,
                notes=notes,
                line_items=line_items,
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

        try:
            quotation = QuotationService.update_draft_quotation(
                user=request.user,
                quotation=quotation,
                terms=terms,
                notes=notes,
                line_items=line_items,
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

        try:
            quotation = QuotationService.create_revision(
                user=request.user,
                quotation=quotation,
                terms=terms,
                notes=notes,
                line_items=line_items,
                revision_reason=revision_reason,
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
