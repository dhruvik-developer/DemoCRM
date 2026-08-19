import datetime
import logging
from decimal import Decimal
from uuid import uuid4

logger = logging.getLogger(__name__)

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from .models import (
    Activity,
    AuditLog,
    Customer,
    Lead,
    LeadSource,
    Pipeline,
    PipelineStage,
    Quotation,
    QuotationApproval,
    QuotationIntegrationEvent,
    QuotationLineItem,
    QuotationStatus,
    QuotationVersion,
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
        requires_quotation=False,
        quotation_approval_required=False,
    ):
        if not pipeline.is_active:
            raise ValidationError("Cannot create a stage inside an inactive pipeline.")

        if display_order < 1:
            raise ValidationError("Display order must be at least 1.")

        stage = PipelineStage.objects.create(
            pipeline=pipeline,
            name=name,
            description=description,
            display_order=display_order,
            requires_quotation=requires_quotation,
            quotation_approval_required=quotation_approval_required,
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
                "requires_quotation": stage.requires_quotation,
                "quotation_approval_required": stage.quotation_approval_required,
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
            raise ValidationError("Cannot create a Lead using an inactive Lead Source.")

        if not pipeline.is_active:
            raise ValidationError("Cannot create a Lead using an inactive Pipeline.")

        if not current_stage.is_active:
            raise ValidationError(
                "Cannot create a Lead using an inactive Pipeline Stage."
            )

        if current_stage.pipeline_id != pipeline.id:
            raise ValidationError(
                "The selected stage does not belong to the selected pipeline."
            )

        if not assigned_to.is_active:
            raise ValidationError("An inactive employee cannot be assigned a Lead.")

        first_stage = (
            PipelineStage.objects.filter(
                pipeline=pipeline,
                is_active=True,
            )
            .order_by("display_order")
            .first()
        )

        if not first_stage:
            raise ValidationError("The selected Pipeline has no active stages.")

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
            raise ValidationError("An inactive employee cannot be assigned a Lead.")

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
        stage_id=None,
    ):
        if lead.status != Lead.Status.ACTIVE:
            raise ValidationError(
                "Only active Leads can progress through the pipeline."
            )

        current_stage = lead.current_stage

        if stage_id:
            target_stage = PipelineStage.objects.filter(
                id=stage_id,
                pipeline=lead.pipeline,
                is_active=True,
            ).first()

            if not target_stage:
                raise ValidationError(
                    "Invalid or inactive stage for this lead's pipeline."
                )

            next_stage = target_stage

        else:
            next_stage = (
                PipelineStage.objects.filter(
                    pipeline=lead.pipeline,
                    is_active=True,
                    display_order__gt=current_stage.display_order,
                )
                .order_by("display_order")
                .first()
            )

            if not next_stage:
                raise ValidationError("There is no next active stage.")

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
            raise ValidationError("Only active Leads can be marked as lost.")

        if not lost_reason:
            raise ValidationError("Lost reason is required.")

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
            raise ValidationError("Only lost Leads can be re-engaged.")

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
        quotation=None,
        notes=None,
        follow_up_required=False,
        follow_up_date=None,
    ):
        if not lead and not customer:
            raise ValidationError("Activity must belong to a Lead or Customer.")

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
            raise ValidationError("Follow-up date is required.")

        if not follow_up_required and follow_up_date:
            raise ValidationError(
                "Follow-up date cannot be provided when follow-up is not required."
            )

        activity = Activity.objects.create(
            lead=lead,
            customer=customer,
            quotation=quotation,
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
                "quotation": str(quotation.id) if quotation else None,
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
        lead = Lead.objects.select_for_update().get(pk=lead.pk)

        if lead.status == Lead.Status.CONVERTED:
            raise ValidationError("This Lead has already been converted.")

        if lead.status != Lead.Status.ACTIVE:
            raise ValidationError("Only active Leads can be converted.")

        accepted_quotation = None
        if lead.current_stage.requires_quotation:
            accepted_quotation = Quotation.objects.filter(
                lead=lead,
                current_version__status=QuotationStatus.ACCEPTED,
            ).first()

            if not accepted_quotation:
                raise ValidationError(
                    "This Lead's quotation must be accepted before it can be converted."
                )

        existing_customer = Customer.objects.filter(email=email).first()

        if existing_customer:
            raise ValidationError("A customer with this email address already exists.")

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

        if accepted_quotation:
            CRMService.create_audit_log(
                user=user,
                entity_type="Lead",
                entity_id=lead.id,
                action="LEAD_CONVERTED_AFTER_QUOTATION_ACCEPTANCE",
                new_value={
                    "quotation": str(accepted_quotation.id),
                    "customer": str(customer.id),
                },
            )

        return customer


class QuotationService:
    @staticmethod
    def generate_quotation_number():
        prefix = f"Q-{timezone.now().strftime('%Y%m')}"
        random_suffix = str(uuid4().hex[:6]).upper()
        number = f"{prefix}-{random_suffix}"
        while Quotation.objects.filter(quotation_number=number).exists():
            random_suffix = str(uuid4().hex[:6]).upper()
            number = f"{prefix}-{random_suffix}"
        return number

    @staticmethod
    @transaction.atomic
    def create_quotation(
        *,
        user,
        lead,
        terms=None,
        notes=None,
        line_items=None,
        assigned_to=None,
    ):
        if lead.status != Lead.Status.ACTIVE:
            raise ValidationError("Cannot create a quotation for a non-active Lead.")

        assigned_user = assigned_to or lead.assigned_to
        approval_required = bool(
            lead.current_stage and lead.current_stage.quotation_approval_required
        )
        quotation_num = QuotationService.generate_quotation_number()

        quotation = Quotation.objects.create(
            quotation_number=quotation_num,
            lead=lead,
            created_by=user,
            status=QuotationStatus.DRAFT,
        )

        version = QuotationVersion.objects.create(
            quotation=quotation,
            version_number=1,
            status=QuotationStatus.DRAFT,
            created_by=user,
            assigned_to=assigned_user,
            pipeline=lead.pipeline,
            current_stage=lead.current_stage,
            approval_required=approval_required,
            terms=terms,
            notes=notes,
            total_amount=Decimal("0.00"),
        )

        total = Decimal("0.00")
        if line_items:
            if isinstance(line_items, str):
                import json

                try:
                    line_items = json.loads(line_items)
                except Exception:
                    line_items = []
            for item in line_items:
                if isinstance(item, str):
                    import json

                    try:
                        item = json.loads(item)
                    except Exception:
                        continue
                if not isinstance(item, dict):
                    continue
                desc = item.get("description", "").strip()
                qty = int(item.get("quantity", 1))
                price = Decimal(str(item.get("unit_price", "0.00")))
                li = QuotationLineItem.objects.create(
                    version=version,
                    description=desc,
                    quantity=qty,
                    unit_price=price,
                )
                total += li.amount

        version.total_amount = total
        version.save(update_fields=["total_amount", "updated_at"])

        quotation.current_version = version
        quotation.status = QuotationStatus.DRAFT
        quotation.save(update_fields=["current_version", "status", "updated_at"])

        CRMService.create_audit_log(
            user=user,
            entity_type="Quotation",
            entity_id=quotation.id,
            action="QUOTATION_CREATED",
            new_value={
                "quotation_number": quotation.quotation_number,
                "lead_id": str(lead.id),
                "version": 1,
                "total_amount": str(total),
            },
        )

        CRMService.create_activity(
            user=user,
            activity_type=Activity.ActivityType.QUOTATION_CREATED,
            outcome=f"Created Quotation {quotation.quotation_number} (v1)",
            lead=lead,
            quotation=quotation,
            notes=f"Total: ${total}",
        )

        logger.info(
            "Quotation created: %s for lead %s (total: %s)",
            quotation.quotation_number,
            lead.id,
            total,
        )

        return quotation

    @staticmethod
    @transaction.atomic
    def update_draft_quotation(
        *,
        user,
        quotation,
        terms=None,
        notes=None,
        line_items=None,
    ):
        version = quotation.current_version
        if not version or version.status != QuotationStatus.DRAFT:
            raise ValidationError(
                "Only draft quotations can be edited directly. Create a revision for sent/approved quotations."
            )

        if terms is not None:
            version.terms = terms
        if notes is not None:
            version.notes = notes

        if line_items is not None:
            if isinstance(line_items, str):
                import json

                try:
                    line_items = json.loads(line_items)
                except Exception:
                    line_items = []
            version.line_items.all().delete()
            total = Decimal("0.00")
            for item in line_items:
                if isinstance(item, str):
                    import json

                    try:
                        item = json.loads(item)
                    except Exception:
                        continue
                if not isinstance(item, dict):
                    continue
                desc = item.get("description", "").strip()
                qty = int(item.get("quantity", 1))
                price = Decimal(str(item.get("unit_price", "0.00")))
                li = QuotationLineItem.objects.create(
                    version=version,
                    description=desc,
                    quantity=qty,
                    unit_price=price,
                )
                total += li.amount
            version.total_amount = total

        version.save()

        CRMService.create_audit_log(
            user=user,
            entity_type="Quotation",
            entity_id=quotation.id,
            action="QUOTATION_UPDATED",
            new_value={
                "version": version.version_number,
                "total_amount": str(version.total_amount),
            },
        )

        CRMService.create_activity(
            user=user,
            activity_type=Activity.ActivityType.QUOTATION_UPDATED,
            outcome=f"Updated draft Quotation {quotation.quotation_number} (v{version.version_number})",
            lead=quotation.lead if not quotation.customer else None,
            customer=quotation.customer,
            quotation=quotation,
        )

        return quotation

    @staticmethod
    @transaction.atomic
    def submit_quotation_for_approval(
        *,
        user,
        quotation,
    ):
        version = quotation.current_version
        if not version:
            raise ValidationError("Quotation has no active version.")

        if version.status not in [QuotationStatus.DRAFT, QuotationStatus.REVISED]:
            raise ValidationError(
                f"Quotation in status '{version.status}' cannot be submitted for approval."
            )

        if version.approval_required:
            version.status = QuotationStatus.PENDING_APPROVAL
            version.save(update_fields=["status", "updated_at"])

            quotation.status = QuotationStatus.PENDING_APPROVAL
            quotation.save(update_fields=["status", "updated_at"])

            QuotationApproval.objects.create(
                version=version,
                submitted_by=user,
                decision=QuotationApproval.Decision.PENDING,
            )

            CRMService.create_audit_log(
                user=user,
                entity_type="Quotation",
                entity_id=quotation.id,
                action="QUOTATION_SUBMITTED",
                new_value={
                    "version": version.version_number,
                    "status": QuotationStatus.PENDING_APPROVAL,
                },
            )

            CRMService.create_activity(
                user=user,
                activity_type=Activity.ActivityType.QUOTATION_SUBMITTED,
                outcome=f"Submitted Quotation {quotation.quotation_number} (v{version.version_number}) for approval",
                lead=quotation.lead if not quotation.customer else None,
                customer=quotation.customer,
                quotation=quotation,
            )
        else:
            version.status = QuotationStatus.APPROVED
            version.approved_at = timezone.now()
            version.save(update_fields=["status", "approved_at", "updated_at"])

            quotation.status = QuotationStatus.APPROVED
            quotation.save(update_fields=["status", "updated_at"])

            CRMService.create_audit_log(
                user=user,
                entity_type="Quotation",
                entity_id=quotation.id,
                action="QUOTATION_APPROVED",
                new_value={
                    "version": version.version_number,
                    "status": QuotationStatus.APPROVED,
                    "auto_approved": True,
                },
            )

            CRMService.create_activity(
                user=user,
                activity_type=Activity.ActivityType.QUOTATION_APPROVED,
                outcome=f"Auto-approved Quotation {quotation.quotation_number} (v{version.version_number}) (no manager approval required)",
                lead=quotation.lead if not quotation.customer else None,
                customer=quotation.customer,
                quotation=quotation,
            )

        return quotation

    @staticmethod
    @transaction.atomic
    def approve_quotation(
        *,
        reviewer_user,
        quotation,
    ):
        quotation = Quotation.objects.select_for_update().get(pk=quotation.pk)
        version = quotation.current_version
        if not version or version.status != QuotationStatus.PENDING_APPROVAL:
            raise ValidationError("Only quotations pending approval can be approved.")

        approval = (
            QuotationApproval.objects.filter(
                version=version, decision=QuotationApproval.Decision.PENDING
            )
            .order_by("-submitted_at")
            .first()
        )

        if not approval:
            raise ValidationError(
                "No pending approval request found for this quotation version."
            )

        is_self_approval = (
            approval.submitted_by_id == reviewer_user.pk
            or version.created_by_id == reviewer_user.pk
            or quotation.created_by_id == reviewer_user.pk
        )

        if is_self_approval and not reviewer_user.is_superuser:
            has_own_perm = (
                reviewer_user.role
                and reviewer_user.role.permissions.filter(
                    codename="approve_own_quotation"
                ).exists()
            )
            if not has_own_perm:
                raise PermissionDenied(
                    "The submitting agent cannot approve their own quotation without the 'approve_own_quotation' permission."
                )

        approval.reviewed_by = reviewer_user
        approval.decision = QuotationApproval.Decision.APPROVED
        approval.reviewed_at = timezone.now()
        approval.save()

        version.status = QuotationStatus.APPROVED
        version.approved_at = timezone.now()
        version.save(update_fields=["status", "approved_at", "updated_at"])

        quotation.status = QuotationStatus.APPROVED
        quotation.save(update_fields=["status", "updated_at"])

        CRMService.create_audit_log(
            user=reviewer_user,
            entity_type="Quotation",
            entity_id=quotation.id,
            action="QUOTATION_APPROVED",
            new_value={
                "version": version.version_number,
                "approved_by": str(reviewer_user.user_id),
            },
        )

        CRMService.create_activity(
            user=reviewer_user,
            activity_type=Activity.ActivityType.QUOTATION_APPROVED,
            outcome=f"Approved Quotation {quotation.quotation_number} (v{version.version_number})",
            lead=quotation.lead if not quotation.customer else None,
            customer=quotation.customer,
            quotation=quotation,
        )

        return quotation

    @staticmethod
    @transaction.atomic
    def reject_quotation_approval(
        *,
        reviewer_user,
        quotation,
        reason=None,
    ):
        quotation = Quotation.objects.select_for_update().get(pk=quotation.pk)
        version = quotation.current_version
        if not version or version.status != QuotationStatus.PENDING_APPROVAL:
            raise ValidationError(
                "Only quotations pending approval can have approval rejected."
            )

        approval = (
            QuotationApproval.objects.filter(
                version=version, decision=QuotationApproval.Decision.PENDING
            )
            .order_by("-submitted_at")
            .first()
        )

        if not approval:
            raise ValidationError(
                "No pending approval request found for this quotation version."
            )

        if approval:
            approval.reviewed_by = reviewer_user
            approval.decision = QuotationApproval.Decision.REJECTED
            approval.reason = reason
            approval.reviewed_at = timezone.now()
            approval.save()

        version.status = QuotationStatus.DRAFT
        version.save(update_fields=["status", "updated_at"])

        quotation.status = QuotationStatus.DRAFT
        quotation.save(update_fields=["status", "updated_at"])

        CRMService.create_audit_log(
            user=reviewer_user,
            entity_type="Quotation",
            entity_id=quotation.id,
            action="QUOTATION_APPROVAL_REJECTED",
            new_value={
                "version": version.version_number,
                "rejected_by": str(reviewer_user.user_id),
                "reason": reason,
            },
        )

        CRMService.create_activity(
            user=reviewer_user,
            activity_type=Activity.ActivityType.QUOTATION_APPROVAL_REJECTED,
            outcome=f"Rejected approval for Quotation {quotation.quotation_number} (v{version.version_number})",
            lead=quotation.lead if not quotation.customer else None,
            customer=quotation.customer,
            quotation=quotation,
            notes=reason,
        )

        return quotation

    @staticmethod
    @transaction.atomic
    def send_quotation(
        *,
        user,
        quotation,
    ):
        quotation = Quotation.objects.select_for_update().get(pk=quotation.pk)
        version = quotation.current_version
        if not version:
            raise ValidationError("Quotation has no active version.")

        if version.status not in [QuotationStatus.APPROVED, QuotationStatus.SENT]:
            raise ValidationError("Only approved quotations can be sent.")

        if version.status in [
            QuotationStatus.SENT,
            QuotationStatus.ACCEPTED,
            QuotationStatus.REJECTED,
        ]:
            raise ValidationError(
                f"Cannot send a quotation that has already been {version.status.lower()}. Create a revision first."
            )

        version.status = QuotationStatus.SENT
        version.sent_at = timezone.now()
        version.save(update_fields=["status", "sent_at", "updated_at"])

        quotation.status = QuotationStatus.SENT
        quotation.save(update_fields=["status", "updated_at"])

        CRMService.create_audit_log(
            user=user,
            entity_type="Quotation",
            entity_id=quotation.id,
            action="QUOTATION_SENT",
            new_value={
                "version": version.version_number,
                "sent_at": version.sent_at.isoformat(),
            },
        )

        CRMService.create_activity(
            user=user,
            activity_type=Activity.ActivityType.QUOTATION_SENT,
            outcome=f"Sent Quotation {quotation.quotation_number} (v{version.version_number}) to client",
            lead=quotation.lead if not quotation.customer else None,
            customer=quotation.customer,
            quotation=quotation,
            follow_up_required=True,
            follow_up_date=timezone.now() + datetime.timedelta(days=3),
        )

        # Emit integration event for Member 3 Task Management (guaranteed idempotent)
        due_date_iso = (timezone.now() + datetime.timedelta(days=3)).isoformat()
        event_payload = {
            "lead_id": str(quotation.lead.id) if quotation.lead else None,
            "customer_id": str(quotation.customer.id) if quotation.customer else None,
            "quotation_id": str(quotation.id),
            "quotation_number": quotation.quotation_number,
            "quotation_version": version.version_number,
            "responsible_agent_id": str(version.assigned_to.user_id),
            "suggested_task_title": f"Follow up on Quotation {quotation.quotation_number} (v{version.version_number})",
            "suggested_due_date": due_date_iso,
            "source": "quotation.followup_required",
        }

        QuotationIntegrationEvent.objects.get_or_create(
            event_type="quotation.followup_required",
            quotation=quotation,
            quotation_version_number=version.version_number,
            defaults={
                "lead": quotation.lead,
                "customer": quotation.customer,
                "payload": event_payload,
                "status": QuotationIntegrationEvent.Status.PENDING,
            },
        )

        return quotation

    @staticmethod
    @transaction.atomic
    def create_revision(
        *,
        user,
        quotation,
        terms=None,
        notes=None,
        line_items=None,
        revision_reason=None,
    ):
        current_version = quotation.current_version
        if not current_version:
            raise ValidationError("Quotation has no version to revise.")

        if current_version.status not in [
            QuotationStatus.SENT,
            QuotationStatus.REVISED,
            QuotationStatus.DRAFT,
            QuotationStatus.APPROVED,
        ]:
            raise ValidationError(
                f"Cannot create revision for quotation in status '{current_version.status}'."
            )

        if current_version.status in [QuotationStatus.SENT, QuotationStatus.APPROVED]:
            current_version.status = QuotationStatus.REVISED
            current_version.save(update_fields=["status", "updated_at"])

        new_version_num = current_version.version_number + 1
        approval_required = bool(
            quotation.lead.current_stage
            and quotation.lead.current_stage.quotation_approval_required
        )

        new_version = QuotationVersion.objects.create(
            quotation=quotation,
            version_number=new_version_num,
            status=QuotationStatus.DRAFT,
            created_by=user,
            assigned_to=current_version.assigned_to,
            pipeline=quotation.lead.pipeline,
            current_stage=quotation.lead.current_stage,
            approval_required=approval_required,
            terms=terms if terms is not None else current_version.terms,
            notes=notes if notes is not None else current_version.notes,
            revision_reason=revision_reason,
            total_amount=Decimal("0.00"),
        )

        total = Decimal("0.00")
        if line_items is not None:
            if isinstance(line_items, str):
                import json

                try:
                    line_items = json.loads(line_items)
                except Exception:
                    line_items = []
            for item in line_items:
                if isinstance(item, str):
                    import json

                    try:
                        item = json.loads(item)
                    except Exception:
                        continue
                if not isinstance(item, dict):
                    continue
                desc = item.get("description", "").strip()
                qty = int(item.get("quantity", 1))
                price = Decimal(str(item.get("unit_price", "0.00")))
                li = QuotationLineItem.objects.create(
                    version=new_version,
                    description=desc,
                    quantity=qty,
                    unit_price=price,
                )
                total += li.amount
        else:
            for item in current_version.line_items.all():
                li = QuotationLineItem.objects.create(
                    version=new_version,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                total += li.amount

        new_version.total_amount = total
        new_version.save(update_fields=["total_amount", "updated_at"])

        quotation.current_version = new_version
        quotation.status = QuotationStatus.DRAFT
        quotation.save(update_fields=["current_version", "status", "updated_at"])

        CRMService.create_audit_log(
            user=user,
            entity_type="Quotation",
            entity_id=quotation.id,
            action="QUOTATION_VERSION_CREATED",
            new_value={
                "version": new_version_num,
                "total_amount": str(total),
            },
        )

        CRMService.create_activity(
            user=user,
            activity_type=Activity.ActivityType.QUOTATION_VERSION_CREATED,
            outcome=f"Created Quotation revision {quotation.quotation_number} (v{new_version_num})",
            lead=quotation.lead if not quotation.customer else None,
            customer=quotation.customer,
            quotation=quotation,
        )

        return quotation

    @staticmethod
    @transaction.atomic
    def accept_quotation(
        *,
        user,
        quotation,
    ):
        quotation = Quotation.objects.select_for_update().get(pk=quotation.pk)
        version = quotation.current_version
        if not version:
            raise ValidationError("Quotation has no active version.")

        if version.status != QuotationStatus.SENT:
            raise ValidationError("Only sent quotations can be accepted.")

        version.status = QuotationStatus.ACCEPTED
        version.accepted_at = timezone.now()
        version.save(update_fields=["status", "accepted_at", "updated_at"])

        quotation.status = QuotationStatus.ACCEPTED
        quotation.accepted_version = version
        quotation.save(update_fields=["status", "accepted_version", "updated_at"])

        CRMService.create_audit_log(
            user=user,
            entity_type="Quotation",
            entity_id=quotation.id,
            action="QUOTATION_ACCEPTED",
            new_value={
                "version": version.version_number,
                "accepted_at": version.accepted_at.isoformat(),
            },
        )

        CRMService.create_activity(
            user=user,
            activity_type=Activity.ActivityType.QUOTATION_ACCEPTED,
            outcome=f"Client accepted Quotation {quotation.quotation_number} (v{version.version_number})",
            lead=quotation.lead if not quotation.customer else None,
            customer=quotation.customer,
            quotation=quotation,
        )

        customer = None
        if quotation.lead and quotation.lead.status == Lead.Status.ACTIVE:
            email = (
                quotation.lead.email
                or f"{quotation.lead.name.lower().replace(' ', '')}@example.com"
            )
            phone = quotation.lead.phone or "0000000000"
            customer = CRMService.convert_lead(
                user=user,
                lead=quotation.lead,
                name=quotation.lead.name,
                email=email,
                phone=phone,
                company_name=quotation.lead.company_name,
            )
            quotation.customer = customer
            quotation.save(update_fields=["customer", "updated_at"])

        return quotation, customer

    @staticmethod
    @transaction.atomic
    def reject_quotation(
        *,
        user,
        quotation,
        rejection_reason,
    ):
        quotation = Quotation.objects.select_for_update().get(pk=quotation.pk)
        version = quotation.current_version
        if not version:
            raise ValidationError("Quotation has no active version.")

        if version.status != QuotationStatus.SENT:
            raise ValidationError("Only sent quotations can be rejected by the client.")

        if not rejection_reason:
            raise ValidationError("Rejection reason is required.")

        version.status = QuotationStatus.REJECTED
        version.rejected_at = timezone.now()
        version.rejection_reason = rejection_reason
        version.save(
            update_fields=["status", "rejected_at", "rejection_reason", "updated_at"]
        )

        quotation.status = QuotationStatus.REJECTED
        quotation.save(update_fields=["status", "updated_at"])

        CRMService.create_audit_log(
            user=user,
            entity_type="Quotation",
            entity_id=quotation.id,
            action="QUOTATION_REJECTED",
            new_value={
                "version": version.version_number,
                "rejection_reason": rejection_reason,
            },
        )

        CRMService.create_activity(
            user=user,
            activity_type=Activity.ActivityType.QUOTATION_REJECTED,
            outcome=f"Client rejected Quotation {quotation.quotation_number} (v{version.version_number})",
            lead=quotation.lead if not quotation.customer else None,
            customer=quotation.customer,
            quotation=quotation,
            notes=rejection_reason,
        )

        if quotation.lead and quotation.lead.status == Lead.Status.ACTIVE:
            CRMService.mark_lead_lost(
                user=user,
                lead=quotation.lead,
                lost_reason=f"Quotation {quotation.quotation_number} rejected: {rejection_reason}",
            )

        return quotation

    @staticmethod
    def send_quotation_email(
        *,
        user,
        quotation,
        version_number=None,
        recipient_email=None,
        subject=None,
        body=None,
    ):
        from django.core.mail import EmailMessage
        from django.conf import settings
        from smtplib import SMTPException
        from .pdf_utils import generate_quotation_pdf

        with transaction.atomic():
            quotation = Quotation.objects.select_for_update().get(pk=quotation.pk)

            if version_number is not None:
                version = quotation.versions.filter(
                    version_number=version_number
                ).first()
                if not version:
                    raise ValidationError(
                        f"Quotation version {version_number} does not exist."
                    )
            else:
                version = quotation.current_version

            if not version:
                raise ValidationError("Quotation has no active version.")

            if version.status in [
                QuotationStatus.DRAFT,
                QuotationStatus.PENDING_APPROVAL,
            ]:
                raise ValidationError(
                    f"Quotation PDF delivery is blocked for version in state '{version.status}'. Approved or sent version required."
                )

            to_email = recipient_email
            if not to_email:
                if quotation.customer and quotation.customer.email:
                    to_email = quotation.customer.email
                elif quotation.lead and quotation.lead.email:
                    to_email = quotation.lead.email

            if not to_email:
                raise ValidationError("Recipient email is required to send quotation.")

            if version.status == QuotationStatus.APPROVED:
                QuotationService.send_quotation(user=user, quotation=quotation)
                version.refresh_from_db()
                quotation.refresh_from_db()

        pdf_bytes = generate_quotation_pdf(version)

        filename = f"{quotation.quotation_number}_v{version.version_number}.pdf"
        email_subject = (
            subject
            or f"Quotation {quotation.quotation_number} (v{version.version_number})"
        )
        email_body = body or (
            f"Dear Customer,\n\n"
            f"Please find attached Quotation {quotation.quotation_number} (v{version.version_number}).\n\n"
            f"Thank you,\nDemoCRM Team"
        )

        email = EmailMessage(
            subject=email_subject,
            body=email_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
            to=[to_email],
        )
        email.attach(filename, pdf_bytes, "application/pdf")

        try:
            email.send(fail_silently=False)
        except (SMTPException, Exception) as exc:
            logger.error(
                "Failed to send quotation email for %s: %s",
                quotation.quotation_number,
                str(exc),
            )
            CRMService.create_audit_log(
                user=user,
                entity_type="Quotation",
                entity_id=quotation.id,
                action="QUOTATION_EMAIL_FAILED",
                new_value={
                    "version": version.version_number,
                    "sent_to": to_email,
                    "error": str(exc),
                },
            )
            raise ValidationError(f"Email delivery failed: {str(exc)}")

        version.sent_to = to_email
        version.save(update_fields=["sent_to", "updated_at"])

        CRMService.create_audit_log(
            user=user,
            entity_type="Quotation",
            entity_id=quotation.id,
            action="QUOTATION_EMAIL_SENT",
            new_value={
                "version": version.version_number,
                "sent_to": to_email,
            },
        )

        if quotation.customer:
            activity_customer = quotation.customer
            activity_lead = None
        else:
            activity_customer = None
            activity_lead = quotation.lead

        CRMService.create_activity(
            user=user,
            activity_type=Activity.ActivityType.QUOTATION_EMAIL_SENT,
            outcome=f"Emailed Quotation {quotation.quotation_number} (v{version.version_number}) to {to_email}",
            lead=activity_lead,
            customer=activity_customer,
            quotation=quotation,
            notes=f"Subject: {email_subject}",
        )

        return quotation, version
