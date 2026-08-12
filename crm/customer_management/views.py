from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics

from .models import (
    Activity,
    AuditLog,
    Customer,
    Lead,
    LeadSource,
    Pipeline,
    PipelineStage,
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
)
from .services import CRMService


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

        source = CRMService.create_lead_source(
            user=request.user,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description"),
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

        pipeline = CRMService.create_pipeline(
            user=request.user,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description"),
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
                display_order=serializer.validated_data["display_order"],
                description=serializer.validated_data.get("description"),
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

        serializer = LeadSerializer(leads, many=True)
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


class LeadDetailView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "GET": "view_lead",
        "PATCH": "change_lead",
        "PUT": "change_lead",
        "DELETE": "delete_lead",
    }

    def get_object(self, pk):
        return get_object_or_404(Lead, pk=pk)

    def get(self, request, pk):
        lead = self.get_object(pk)
        serializer = LeadSerializer(lead)
        return Response(serializer.data)

    def patch(self, request, pk):
        lead = self.get_object(pk)
        old_data = {
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "company_name": lead.company_name,
            "source": str(lead.source_id) if lead.source_id else None,
            "assigned_to": str(lead.assigned_to_id) if lead.assigned_to_id else None,
            "pipeline": str(lead.pipeline_id) if lead.pipeline_id else None,
            "current_stage": str(lead.current_stage_id) if lead.current_stage_id else None,
        }

        serializer = LeadSerializer(
            lead,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated_lead = serializer.save()

        new_data = {
            "name": updated_lead.name,
            "email": updated_lead.email,
            "phone": updated_lead.phone,
            "company_name": updated_lead.company_name,
            "source": str(updated_lead.source_id) if updated_lead.source_id else None,
            "assigned_to": str(updated_lead.assigned_to_id) if updated_lead.assigned_to_id else None,
            "pipeline": str(updated_lead.pipeline_id) if updated_lead.pipeline_id else None,
            "current_stage": str(updated_lead.current_stage_id) if updated_lead.current_stage_id else None,
        }

        if old_data != new_data:
            CRMService.create_audit_log(
                user=request.user,
                entity_type="Lead",
                entity_id=updated_lead.id,
                action="LEAD_UPDATED",
                old_value=old_data,
                new_value=new_data,
            )

        return Response(serializer.data)

    def put(self, request, pk):
        lead = self.get_object(pk)
        old_data = {
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "company_name": lead.company_name,
            "source": str(lead.source_id) if lead.source_id else None,
            "assigned_to": str(lead.assigned_to_id) if lead.assigned_to_id else None,
            "pipeline": str(lead.pipeline_id) if lead.pipeline_id else None,
            "current_stage": str(lead.current_stage_id) if lead.current_stage_id else None,
        }

        serializer = LeadSerializer(
            lead,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        updated_lead = serializer.save()

        new_data = {
            "name": updated_lead.name,
            "email": updated_lead.email,
            "phone": updated_lead.phone,
            "company_name": updated_lead.company_name,
            "source": str(updated_lead.source_id) if updated_lead.source_id else None,
            "assigned_to": str(updated_lead.assigned_to_id) if updated_lead.assigned_to_id else None,
            "pipeline": str(updated_lead.pipeline_id) if updated_lead.pipeline_id else None,
            "current_stage": str(updated_lead.current_stage_id) if updated_lead.current_stage_id else None,
        }

        if old_data != new_data:
            CRMService.create_audit_log(
                user=request.user,
                entity_type="Lead",
                entity_id=updated_lead.id,
                action="LEAD_UPDATED",
                old_value=old_data,
                new_value=new_data,
            )

        return Response(serializer.data)

    def delete(self, request, pk):
        lead = self.get_object(pk)
        lead.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


class LeadAssignView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "PATCH": "assign_lead",
    }

    def patch(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)

        new_assignee_id = request.data.get("assigned_to")

        if not new_assignee_id:
            return Response(
                {"detail": "assigned_to is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()

        new_assignee = get_object_or_404(
            User,
            pk=new_assignee_id,
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

        return Response(LeadSerializer(lead).data)


class LeadProgressView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "progress_lead",
    }

    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)

        try:
            lead = CRMService.progress_lead(
                user=request.user,
                lead=lead,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(LeadSerializer(lead).data)


class LeadLostView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "mark_lead_lost",
    }

    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)

        lost_reason = request.data.get("lost_reason")

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

        return Response(LeadSerializer(lead).data)


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

        return Response(LeadSerializer(lead).data)


class LeadConvertView(APIView):
    permission_classes = [CRMHasPermission]

    permission_names = {
        "POST": "convert_lead",
    }

    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)

        required_fields = [
            "name",
            "email",
            "phone",
        ]

        missing_fields = [
            field
            for field in required_fields
            if not request.data.get(field)
        ]

        if missing_fields:
            return Response(
                {
                    "detail": (
                        "Missing required fields: "
                        + ", ".join(missing_fields)
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            customer = CRMService.convert_lead(
                user=request.user,
                lead=lead,
                name=request.data["name"],
                email=request.data["email"],
                phone=request.data["phone"],
                company_name=request.data.get("company_name"),
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .serializers import CustomerSerializer

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