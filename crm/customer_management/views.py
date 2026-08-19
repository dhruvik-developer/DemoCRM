import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

User = get_user_model()
logger = logging.getLogger(__name__)

from rest_framework import generics, status
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
    QuotationVersion,
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
    QuotationVersionSerializer,
)
from .services import CRMService, QuotationService
from .pdf_utils import generate_quotation_pdf


class LeadSourceListCreateView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_leadsource",
        "POST": "manage_lead_source",
    }

    def get(self, request):
        sources = LeadSource.objects.all()
        serializer = LeadSourceSerializer(sources, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LeadSourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            source = CRMService.create_lead_source(
                user=request.user,
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get(
                    "description"
                ),
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


class PipelineListCreateView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_pipeline",
        "POST": "manage_pipeline",
    }

    def get(self, request):
        pipelines = Pipeline.objects.all()
        serializer = PipelineSerializer(pipelines, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PipelineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pipeline = CRMService.create_pipeline(
                user=request.user,
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get(
                    "description"
                ),
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


class PipelineStageListCreateView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_pipelinestage",
        "POST": "manage_pipeline_stage",
    }

    def get(self, request):
        stages = PipelineStage.objects.all()
        serializer = PipelineStageSerializer(stages, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PipelineStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage = CRMService.create_pipeline_stage(
                user=request.user,
                pipeline=serializer.validated_data["pipeline"],
                name=serializer.validated_data["name"],
                display_order=serializer.validated_data[
                    "display_order"
                ],
                description=serializer.validated_data.get(
                    "description"
                ),
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


class LeadListCreateView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_lead",
        "POST": "add_lead",
    }

    def get(self, request):
        leads = (
            Lead.objects
            .select_related(
                "source",
                "assigned_to",
                "pipeline",
                "current_stage",
            )
            .all()
        )

        serializer = LeadSerializer(
            leads,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = LeadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            lead = CRMService.create_lead(
                user=request.user,
                name=serializer.validated_data["name"],
                email=serializer.validated_data.get("email"),
                phone=serializer.validated_data.get("phone"),
                company_name=serializer.validated_data.get(
                    "company_name"
                ),
                source=serializer.validated_data["source"],
                assigned_to=serializer.validated_data[
                    "assigned_to"
                ],
                pipeline=serializer.validated_data["pipeline"],
                current_stage=serializer.validated_data[
                    "current_stage"
                ],
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


class LeadDetailView(generics.RetrieveUpdateAPIView):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_lead",
        "PUT": "change_lead",
        "PATCH": "change_lead",
    }

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


class LeadAssignView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "assign_lead",
    }

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


class LeadProgressView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "progress_lead",
    }

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


class LeadLostView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "mark_lead_lost",
    }

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


class LeadReengageView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "reengage_lead",
    }

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


class LeadConvertView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "convert_lead",
    }

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


class ActivityListCreateView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_activity",
        "POST": "add_activity",
    }

    def get(self, request):
        activities = (
            Activity.objects
            .select_related(
                "lead",
                "customer",
                "created_by",
            )
            .all()
        )

        serializer = ActivitySerializer(
            activities,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = ActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            activity = CRMService.create_activity(
                user=request.user,
                activity_type=serializer.validated_data[
                    "activity_type"
                ],
                outcome=serializer.validated_data["outcome"],
                lead=serializer.validated_data.get("lead"),
                customer=serializer.validated_data.get("customer"),
                notes=serializer.validated_data.get("notes"),
                follow_up_required=serializer.validated_data.get(
                    "follow_up_required",
                    False,
                ),
                follow_up_date=serializer.validated_data.get(
                    "follow_up_date"
                ),
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


class AuditLogListView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_auditlog",
    }

    def get(self, request):
        logs = (
            AuditLog.objects
            .select_related("user")
            .all()
        )

        serializer = AuditLogSerializer(
            logs,
            many=True,
        )

        return Response(serializer.data)


class CustomerListCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_customer",
        "POST": "add_customer",
    }

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


class CustomerDetailView(generics.RetrieveAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_customer",
    }


class CustomerActivityListView(generics.ListAPIView):
    serializer_class = ActivitySerializer
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_activity",
    }

    def get_queryset(self):
        customer_id = self.kwargs["pk"]

        return (
            Activity.objects
            .filter(customer_id=customer_id)
            .select_related("customer", "created_by")
            .order_by("-created_at")
        )


# ==============================================================================
# QUOTATION WORKFLOW VIEWS (MEMBER 2)
# ==============================================================================

class QuotationListCreateView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "view_quotation",
        "POST": "add_quotation",
    }

    def get(self, request):
        lead_id = request.query_params.get("lead")
        queryset = Quotation.objects.select_related(
            "lead", "customer", "created_by", "current_version",
            "current_version__created_by", "current_version__assigned_to",
            "current_version__pipeline", "current_version__current_stage"
        ).prefetch_related(
            "current_version__line_items", "current_version__approvals",
            "versions", "versions__line_items", "versions__approvals"
        )

        if lead_id:
            queryset = queryset.filter(lead_id=lead_id)

        serializer = QuotationSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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


class QuotationDetailView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "view_quotation",
    }

    def get(self, request, pk):
        quotation = get_object_or_404(
            Quotation.objects.select_related(
                "lead", "customer", "created_by", "current_version"
            ).prefetch_related("versions", "versions__line_items", "versions__approvals"),
            pk=pk,
        )
        serializer = QuotationSerializer(quotation)
        return Response(serializer.data, status=status.HTTP_200_OK)


class QuotationUpdateDraftView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "PATCH": "change_quotation",
        "PUT": "change_quotation",
    }

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


class QuotationSubmitView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "submit_quotation",
    }

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


class QuotationApproveView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "approve_quotation",
    }

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


class QuotationRejectApprovalView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "approve_quotation",
    }

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


class QuotationSendView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "send_quotation",
    }

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


class QuotationRevisionView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "request_quotation_revision",
    }

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        terms = request.data.get("terms")
        notes = request.data.get("notes")
        line_items = request.data.get("line_items")
        revision_reason = request.data.get("revision_reason") or request.data.get("reason")

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


class QuotationAcceptView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "accept_quotation",
    }

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


class QuotationRejectView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "reject_quotation",
    }

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        rejection_reason = request.data.get("rejection_reason") or request.data.get("reason")

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


class QuotationIntegrationEventListView(generics.ListAPIView):
    queryset = QuotationIntegrationEvent.objects.all()
    serializer_class = QuotationIntegrationEventSerializer
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "view_quotation",
    }


class QuotationPDFView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "GET": "generate_quotation_pdf",
    }

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
                {"detail": f"PDF download is not allowed for quotations in state '{version.status}'."},
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


class QuotationSendEmailView(APIView):
    permission_classes = [CRMHasPermission]
    permission_names = {
        "POST": "send_quotation",
    }

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