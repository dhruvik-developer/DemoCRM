from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    Activity,
    AuditLog,
    Customer,
    Lead,
    LeadSource,
    Pipeline,
    PipelineStage,
)


class CRMService:

    # ---------------------------------------------------------
    # AUDIT LOG
    # ---------------------------------------------------------

    @staticmethod
    def create_audit_log(
        *,
        user,
        entity_type,
        entity_id,
        action,
        old_value=None,
        new_value=None,
        metadata=None,
    ):
        return AuditLog.objects.create(
            user=user,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata,
        )

    # ---------------------------------------------------------
    # LEAD SOURCE
    # ---------------------------------------------------------

    @staticmethod
    def create_lead_source(
        *,
        user,
        name,
        description=None,
    ):
        source = LeadSource.objects.create(
            name=name,
            description=description,
            created_by=user,
        )

        CRMService.create_audit_log(
            user=user,
            entity_type="LeadSource",
            entity_id=source.id,
            action="LEAD_SOURCE_CREATED",
            new_value={
                "name": source.name,
                "description": source.description,
            },
        )

        return source

    # ---------------------------------------------------------
    # PIPELINE
    # ---------------------------------------------------------

    @staticmethod
    def create_pipeline(
        *,
        user,
        name,
        description=None,
    ):
        pipeline = Pipeline.objects.create(
            name=name,
            description=description,
            created_by=user,
        )

        CRMService.create_audit_log(
            user=user,
            entity_type="Pipeline",
            entity_id=pipeline.id,
            action="PIPELINE_CREATED",
            new_value={
                "name": pipeline.name,
                "description": pipeline.description,
            },
        )

        return pipeline

    # ---------------------------------------------------------
    # PIPELINE STAGE
    # ---------------------------------------------------------

    @staticmethod
    def create_pipeline_stage(
        *,
        user,
        pipeline,
        name,
        display_order,
        description=None,
    ):
        if not pipeline.is_active:
            raise ValidationError(
                "Cannot create a stage inside an inactive pipeline."
            )

        if display_order < 1:
            raise ValidationError(
                "Display order must be at least 1."
            )

        stage = PipelineStage.objects.create(
            pipeline=pipeline,
            name=name,
            description=description,
            display_order=display_order,
        )

        CRMService.create_audit_log(
            user=user,
            entity_type="PipelineStage",
            entity_id=stage.id,
            action="PIPELINE_STAGE_CREATED",
            new_value={
                "pipeline": str(pipeline.id),
                "name": stage.name,
                "display_order": stage.display_order,
            },
        )

        return stage

    # ---------------------------------------------------------
    # LEAD CREATION
    # ---------------------------------------------------------

    @staticmethod
    def create_lead(
        *,
        user,
        name,
        source,
        assigned_to,
        pipeline,
        current_stage,
        email=None,
        phone=None,
        company_name=None,
    ):
        if not source.is_active:
            raise ValidationError(
                "Cannot create a Lead using an inactive Lead Source."
            )

        if not pipeline.is_active:
            raise ValidationError(
                "Cannot create a Lead using an inactive Pipeline."
            )

        if not current_stage.is_active:
            raise ValidationError(
                "Cannot create a Lead using an inactive Pipeline Stage."
            )

        if current_stage.pipeline_id != pipeline.id:
            raise ValidationError(
                "The selected stage does not belong to the selected pipeline."
            )

        if not assigned_to.is_active:
            raise ValidationError(
                "An inactive employee cannot be assigned a Lead."
            )

        # A new Lead must start at the first active stage.
        first_stage = (
            PipelineStage.objects
            .filter(
                pipeline=pipeline,
                is_active=True,
            )
            .order_by("display_order")
            .first()
        )

        if not first_stage:
            raise ValidationError(
                "The selected Pipeline has no active stages."
            )

        if current_stage.id != first_stage.id:
            raise ValidationError(
                "A new Lead must start at the first active Pipeline Stage."
            )

        lead = Lead.objects.create(
            name=name,
            email=email,
            phone=phone,
            company_name=company_name,
            source=source,
            assigned_to=assigned_to,
            pipeline=pipeline,
            current_stage=current_stage,
            status=Lead.Status.ACTIVE,
        )

        CRMService.create_audit_log(
            user=user,
            entity_type="Lead",
            entity_id=lead.id,
            action="LEAD_CREATED",
            new_value={
                "name": lead.name,
                "assigned_to": str(assigned_to.user_id),
                "source": str(source.id),
                "pipeline": str(pipeline.id),
                "current_stage": str(current_stage.id),
            },
        )

        return lead

    # ---------------------------------------------------------
    # ASSIGN LEAD
    # ---------------------------------------------------------

    @staticmethod
    def assign_lead(
        *,
        user,
        lead,
        new_assignee,
    ):
        if not new_assignee.is_active:
            raise ValidationError(
                "An inactive employee cannot be assigned a Lead."
            )

        old_assignee = lead.assigned_to

        if old_assignee.user_id == new_assignee.user_id:
            return lead

        lead.assigned_to = new_assignee
        lead.save(update_fields=["assigned_to", "updated_at"])

        CRMService.create_audit_log(
            user=user,
            entity_type="Lead",
            entity_id=lead.id,
            action="LEAD_ASSIGNED",
            old_value={
                "assigned_to": str(old_assignee.user_id),
            },
            new_value={
                "assigned_to": str(new_assignee.user_id),
            },
        )

        return lead

    # ---------------------------------------------------------
    # MOVE LEAD TO NEXT STAGE
    # ---------------------------------------------------------

    @staticmethod
    def progress_lead(
        *,
        user,
        lead,
    ):
        if lead.status != Lead.Status.ACTIVE:
            raise ValidationError(
                "Only active Leads can progress through the pipeline."
            )

        current_stage = lead.current_stage

        next_stage = (
            PipelineStage.objects
            .filter(
                pipeline=lead.pipeline,
                is_active=True,
                display_order__gt=current_stage.display_order,
            )
            .order_by("display_order")
            .first()
        )

        if not next_stage:
            raise ValidationError(
                "There is no next active stage."
            )

        old_stage = current_stage

        lead.current_stage = next_stage
        lead.save(update_fields=["current_stage", "updated_at"])

        CRMService.create_audit_log(
            user=user,
            entity_type="Lead",
            entity_id=lead.id,
            action="STAGE_CHANGED",
            old_value={
                "stage": str(old_stage.id),
                "stage_name": old_stage.name,
            },
            new_value={
                "stage": str(next_stage.id),
                "stage_name": next_stage.name,
            },
        )

        return lead

    # ---------------------------------------------------------
    # MARK LEAD LOST
    # ---------------------------------------------------------

    @staticmethod
    def mark_lead_lost(
        *,
        user,
        lead,
        lost_reason,
    ):
        if lead.status != Lead.Status.ACTIVE:
            raise ValidationError(
                "Only active Leads can be marked as lost."
            )

        if not lost_reason:
            raise ValidationError(
                "Lost reason is required."
            )

        lead.status = Lead.Status.LOST
        lead.lost_reason = lost_reason
        lead.lost_at = timezone.now()

        lead.save(
            update_fields=[
                "status",
                "lost_reason",
                "lost_at",
                "updated_at",
            ]
        )

        CRMService.create_audit_log(
            user=user,
            entity_type="Lead",
            entity_id=lead.id,
            action="LEAD_LOST",
            old_value={
                "status": Lead.Status.ACTIVE,
            },
            new_value={
                "status": Lead.Status.LOST,
                "lost_reason": lost_reason,
            },
        )

        return lead

    # ---------------------------------------------------------
    # RE-ENGAGE LEAD
    # ---------------------------------------------------------

    @staticmethod
    def reengage_lead(
        *,
        user,
        lead,
    ):
        if lead.status != Lead.Status.LOST:
            raise ValidationError(
                "Only lost Leads can be re-engaged."
            )

        old_status = lead.status

        lead.status = Lead.Status.ACTIVE
        lead.lost_reason = None
        lead.lost_at = None

        lead.save(
            update_fields=[
                "status",
                "lost_reason",
                "lost_at",
                "updated_at",
            ]
        )

        CRMService.create_audit_log(
            user=user,
            entity_type="Lead",
            entity_id=lead.id,
            action="LEAD_REENGAGED",
            old_value={
                "status": old_status,
            },
            new_value={
                "status": Lead.Status.ACTIVE,
            },
        )

        return lead

    # ---------------------------------------------------------
    # CREATE ACTIVITY
    # ---------------------------------------------------------

    @staticmethod
    def create_activity(
        *,
        user,
        activity_type,
        outcome,
        lead=None,
        customer=None,
        notes=None,
        follow_up_required=False,
        follow_up_date=None,
    ):
        if not lead and not customer:
            raise ValidationError(
                "Activity must belong to a Lead or Customer."
            )

        if lead and customer:
            raise ValidationError(
                "Activity cannot belong to both a Lead and a Customer."
            )

        if lead:
            lead_obj = Lead.objects.filter(pk=lead.pk).values("status").first()
            if lead_obj and lead_obj["status"] == Lead.Status.CONVERTED:
                raise ValidationError(
                    "Cannot create a new Activity for a converted Lead. Create the Activity against the Customer instead."
                )

        if follow_up_required and not follow_up_date:
            raise ValidationError(
                "Follow-up date is required."
            )

        if not follow_up_required and follow_up_date:
            raise ValidationError(
                "Follow-up date cannot be provided when follow-up is not required."
            )

        activity = Activity.objects.create(
            lead=lead,
            customer=customer,
            created_by=user,
            activity_type=activity_type,
            outcome=outcome,
            notes=notes,
            follow_up_required=follow_up_required,
            follow_up_date=follow_up_date,
        )

        CRMService.create_audit_log(
            user=user,
            entity_type="Activity",
            entity_id=activity.id,
            action="ACTIVITY_CREATED",
            new_value={
                "activity_type": activity.activity_type,
                "lead": str(lead.id) if lead else None,
                "customer": str(customer.id) if customer else None,
            },
        )

        return activity

    # ---------------------------------------------------------
    # LEAD CONVERSION
    # ---------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def convert_lead(
        *,
        user,
        lead,
        name,
        email,
        phone,
        company_name=None,
    ):
        # Lock the Lead so two conversion requests
        # cannot process it simultaneously.
        lead = (
            Lead.objects
            .select_for_update()
            .get(pk=lead.pk)
        )

        if lead.status == Lead.Status.CONVERTED:
            raise ValidationError(
                "This Lead has already been converted."
            )

        if lead.status != Lead.Status.ACTIVE:
            raise ValidationError(
                "Only active Leads can be converted."
            )

        # Customer duplicate check.
        existing_customer = (
            Customer.objects
            .filter(email=email)
            .first()
        )

        if existing_customer:
            raise ValidationError(
                "A customer with this email address already exists."
            )

        customer = Customer.objects.create(
            lead=lead,
            name=name,
            email=email,
            phone=phone,
            company_name=company_name,
        )

        old_status = lead.status

        lead.status = Lead.Status.CONVERTED
        lead.save(update_fields=["status", "updated_at"])

        CRMService.create_audit_log(
            user=user,
            entity_type="Lead",
            entity_id=lead.id,
            action="LEAD_CONVERTED",
            old_value={
                "status": old_status,
            },
            new_value={
                "status": Lead.Status.CONVERTED,
                "customer": str(customer.id),
            },
        )

        return customer