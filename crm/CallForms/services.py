from decimal import Decimal
import logging
from datetime import datetime, time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction, models
from django.utils import timezone, dateparse

from Notification.models import NotificationEventType
from Notification.notification_utils import trigger_notification_event
from customer_management.services import CRMService

from .models import (
    AdhocFieldProposal,
    AssigneeRuleChoice,
    CallAttempt,
    CallTemplate,
    ConditionChoice,
    FieldType,
    FormSubmission,
    IndexedSubmissionValue,
    OutcomeChoice,
    PipelineStageActivity,
    ProposalStatus,
    TaskTriggerRule,
    TemplateField,
    TemplateVersion,
)

logger = logging.getLogger(__name__)


def create_template_with_initial_version(
    name, description, created_by, initial_fields=None
):
    """
    Atomically creates a CallTemplate along with its initial V1 primary TemplateVersion
    and optional initial fields.
    """
    with transaction.atomic():
        template = CallTemplate.objects.create(
            name=name,
            description=description,
            created_by=created_by,
        )

        version = TemplateVersion.objects.create(
            template=template,
            version_number=1,
            version_label="v1.0",
            is_primary=True,
            created_by=created_by,
        )

        if initial_fields:
            for idx, field_data in enumerate(initial_fields, start=1):
                TemplateField.objects.create(
                    template_version=version,
                    field_key=field_data["field_key"],
                    label=field_data["label"],
                    field_type=field_data.get("field_type", FieldType.TEXT),
                    is_required=field_data.get("is_required", False),
                    display_order=field_data.get("display_order", idx),
                    help_text=field_data.get("help_text", ""),
                    options=field_data.get("options", []),
                    validation_rules=field_data.get("validation_rules", {}),
                )

        logger.info(
            "Created CallTemplate '%s' (id=%s) with initial version v1.0",
            template.name,
            template.id,
        )

        CRMService.create_audit_log(
            user=created_by,
            entity_type="CallTemplate",
            entity_id=template.id,
            action="CALL_TEMPLATE_CREATED",
            new_value={"name": template.name},
        )

        return template, version


def set_primary_version(template_or_id, version_or_id):
    """
    Atomically sets a specific TemplateVersion as the primary/default version for its template.
    """
    with transaction.atomic():
        if isinstance(template_or_id, CallTemplate):
            template = template_or_id
        else:
            template = CallTemplate.objects.get(pk=template_or_id)

        if isinstance(version_or_id, TemplateVersion):
            version = version_or_id
        else:
            version = TemplateVersion.objects.get(pk=version_or_id)

        if version.template_id != template.id:
            raise ValidationError(
                "The specified version does not belong to this template."
            )

        # Clear primary flag on all versions for this template
        template.versions.update(is_primary=False)

        version.is_primary = True
        version.save(update_fields=["is_primary"])

        logger.info(
            "Set TemplateVersion %s (v%s) as primary for CallTemplate %s",
            version.id,
            version.version_number,
            template.name,
        )
        return version


def clone_template_version(
    source_version_or_id, created_by, new_label=None, set_primary=True
):
    """
    Clones an existing TemplateVersion and all of its fields into a new version v(N+1).
    """
    with transaction.atomic():
        if isinstance(source_version_or_id, TemplateVersion):
            source_version = source_version_or_id
        else:
            source_version = TemplateVersion.objects.get(pk=source_version_or_id)

        template = source_version.template

        # Get highest existing version number
        max_num = (
            template.versions.aggregate(max_num=models.Max("version_number"))["max_num"]
            or 0
        )
        next_version_num = max_num + 1

        if set_primary:
            template.versions.update(is_primary=False)

        new_version = TemplateVersion.objects.create(
            template=template,
            version_number=next_version_num,
            version_label=new_label or f"v{next_version_num}.0",
            is_primary=set_primary,
            created_by=created_by,
        )

        # Copy all fields
        source_fields = source_version.fields.all()
        for field in source_fields:
            TemplateField.objects.create(
                template_version=new_version,
                field_key=field.field_key,
                label=field.label,
                field_type=field.field_type,
                is_required=field.is_required,
                display_order=field.display_order,
                help_text=field.help_text,
                options=field.options,
                validation_rules=field.validation_rules,
            )

        logger.info(
            "Cloned TemplateVersion %s (v%s) into new version %s (v%s) for CallTemplate %s",
            source_version.id,
            source_version.version_number,
            new_version.id,
            new_version.version_number,
            template.name,
        )

        CRMService.create_audit_log(
            user=created_by,
            entity_type="TemplateVersion",
            entity_id=new_version.id,
            action="CALL_TEMPLATE_VERSIONED",
            new_value={
                "template": str(template.id),
                "version_number": new_version.version_number,
                "cloned_from": str(source_version.id),
            },
        )

        return new_version


def reorder_template_fields(version_or_id, field_order_list):
    """
    Bulk updates the display_order of fields belonging to an unlocked TemplateVersion.
    field_order_list is expected to be a list of dicts: [{'field_id': ..., 'display_order': ...}, ...]
    """
    with transaction.atomic():
        if isinstance(version_or_id, TemplateVersion):
            version = version_or_id
        else:
            version = TemplateVersion.objects.get(pk=version_or_id)

        if version.is_locked:
            raise ValidationError("Cannot reorder fields on a locked template version.")

        updated_fields = []
        for item in field_order_list:
            field_id = item.get("field_id")
            order = item.get("display_order")
            if field_id and order is not None:
                field = version.fields.get(pk=field_id)
                field.display_order = order
                field.save(update_fields=["display_order"])
                updated_fields.append(field)

        return updated_fields


def create_stage_activity(
    stage,
    name,
    description="",
    activity_type="CALL",
    call_template=None,
    is_primary=False,
    display_order=1,
    created_by=None,
):
    """
    Atomically creates a PipelineStageActivity and manages primary activity flag for the stage.
    """
    with transaction.atomic():
        if is_primary:
            stage.activities.update(is_primary=False)

        activity = PipelineStageActivity.objects.create(
            stage=stage,
            name=name,
            description=description,
            activity_type=activity_type,
            call_template=call_template,
            is_primary=is_primary,
            display_order=display_order,
            created_by=created_by,
        )
        logger.info(
            "Created PipelineStageActivity '%s' (id=%s) for PipelineStage '%s'",
            activity.name,
            activity.id,
            stage.name,
        )
        return activity


def set_primary_stage_activity(stage_or_id, activity_or_id):
    """
    Atomically sets a PipelineStageActivity as the primary/default activity for its stage.
    """
    from customer_management.models import PipelineStage

    with transaction.atomic():
        if isinstance(stage_or_id, PipelineStage):
            stage = stage_or_id
        else:
            stage = PipelineStage.objects.get(pk=stage_or_id)

        if isinstance(activity_or_id, PipelineStageActivity):
            activity = activity_or_id
        else:
            activity = PipelineStageActivity.objects.get(pk=activity_or_id)

        if activity.stage_id != stage.id:
            raise ValidationError(
                "The specified activity does not belong to this pipeline stage."
            )

        stage.activities.update(is_primary=False)

        activity.is_primary = True
        activity.save(update_fields=["is_primary"])

        logger.info(
            "Set PipelineStageActivity '%s' (id=%s) as primary for PipelineStage '%s'",
            activity.name,
            activity.id,
            stage.name,
        )
        return activity


def get_lead_stage_primary_form(lead_or_id):
    """
    Resolves a Lead's current pipeline stage, finds its primary activity,
    and returns the associated CallTemplate, primary TemplateVersion, and dynamic field schema.
    """
    from customer_management.models import Lead

    if isinstance(lead_or_id, Lead):
        lead = lead_or_id
    else:
        lead = Lead.objects.get(pk=lead_or_id)

    stage = lead.current_stage
    if not stage:
        raise ValidationError("Lead has no assigned pipeline stage.")

    # Find primary activity or fallback to first active activity
    primary_activity = (
        stage.activities.filter(is_primary=True, is_active=True).first()
        or stage.activities.filter(is_active=True).first()
    )

    if not primary_activity:
        return {
            "lead_id": str(lead.id),
            "lead_name": lead.name,
            "stage_id": str(stage.id),
            "stage_name": stage.name,
            "activity": None,
            "call_template": None,
            "template_version": None,
            "fields": [],
        }

    template = primary_activity.call_template
    if not template or not template.is_active:
        return {
            "lead_id": str(lead.id),
            "lead_name": lead.name,
            "stage_id": str(stage.id),
            "stage_name": stage.name,
            "activity": {
                "id": str(primary_activity.id),
                "name": primary_activity.name,
                "activity_type": primary_activity.activity_type,
                "is_primary": primary_activity.is_primary,
            },
            "call_template": None,
            "template_version": None,
            "fields": [],
        }

    # Find primary version or fallback to first active version
    primary_version = (
        template.versions.filter(is_primary=True, is_active=True).first()
        or template.versions.filter(is_active=True).first()
    )

    fields_data = []
    if primary_version:
        fields = primary_version.fields.all()
        for f in fields:
            fields_data.append(
                {
                    "id": str(f.id),
                    "field_key": f.field_key,
                    "label": f.label,
                    "field_type": f.field_type,
                    "is_required": f.is_required,
                    "display_order": f.display_order,
                    "help_text": f.help_text,
                    "options": f.options,
                    "validation_rules": f.validation_rules,
                }
            )

    return {
        "lead_id": str(lead.id),
        "lead_name": lead.name,
        "stage_id": str(stage.id),
        "stage_name": stage.name,
        "activity": {
            "id": str(primary_activity.id),
            "name": primary_activity.name,
            "activity_type": primary_activity.activity_type,
            "is_primary": primary_activity.is_primary,
        },
        "call_template": {
            "id": str(template.id),
            "name": template.name,
            "description": template.description,
        },
        "template_version": (
            {
                "id": str(primary_version.id),
                "version_number": primary_version.version_number,
                "version_label": primary_version.version_label,
                "is_locked": primary_version.is_locked,
            }
            if primary_version
            else None
        ),
        "fields": fields_data,
    }


def log_call_attempt(
    lead_or_id,
    agent,
    stage_or_id=None,
    activity_or_id=None,
    template_version_or_id=None,
    outcome=OutcomeChoice.NO_ANSWER,
    notes="",
    start_time=None,
    end_time=None,
    threshold=None,
):
    """
    Logs a phone call attempt for a lead, calculating sequential attempt_number
    and checking if max failed attempt threshold is reached.

    The threshold defaults to the CALL_FORMS_MAX_FAILED_ATTEMPTS setting.
    When the threshold is hit, ``suggest_mark_lost`` is flagged on the attempt;
    the real outcome is never overwritten.
    """
    from customer_management.models import Lead, PipelineStage

    if threshold is None:
        threshold = getattr(settings, "CALL_FORMS_MAX_FAILED_ATTEMPTS", 5)

    with transaction.atomic():
        # Lock the lead row so concurrent attempts cannot compute duplicate
        # attempt numbers (same pattern as CRMService.convert_lead).
        # Accept either a Lead instance or a raw PK.
        lead_pk = lead_or_id.pk if isinstance(lead_or_id, Lead) else lead_or_id
        lead = Lead.objects.select_for_update().get(pk=lead_pk)

        stage = None
        if stage_or_id:
            stage = (
                stage_or_id
                if isinstance(stage_or_id, PipelineStage)
                else PipelineStage.objects.get(pk=stage_or_id)
            )
        else:
            stage = lead.current_stage

        activity = None
        if activity_or_id:
            activity = (
                activity_or_id
                if isinstance(activity_or_id, PipelineStageActivity)
                else PipelineStageActivity.objects.get(pk=activity_or_id)
            )

        template_version = None
        if template_version_or_id:
            template_version = (
                template_version_or_id
                if isinstance(template_version_or_id, TemplateVersion)
                else TemplateVersion.objects.get(pk=template_version_or_id)
            )

        attempt_number = lead.call_attempts.count() + 1

        attempt = CallAttempt.objects.create(
            lead=lead,
            stage=stage,
            activity=activity,
            template_version=template_version,
            attempt_number=attempt_number,
            agent=agent,
            outcome=outcome,
            notes=notes,
            start_time=start_time or timezone.now(),
            end_time=end_time,
            is_form_submitted=False,
        )

        # Count consecutive unsuccessful attempts for this lead
        recent_attempts = list(
            lead.call_attempts.order_by("-attempt_number")[:threshold]
        )
        failed_count = 0
        for att in recent_attempts:
            if att.outcome in [
                OutcomeChoice.NO_ANSWER,
                OutcomeChoice.BUSY,
                OutcomeChoice.CALLBACK,
            ]:
                failed_count += 1
            else:
                break

        suggest_mark_lost = failed_count >= threshold

        if suggest_mark_lost:
            # Flag the suggestion without corrupting the real outcome history.
            attempt.suggest_mark_lost = True
            attempt.save(update_fields=["suggest_mark_lost"])

        CRMService.create_audit_log(
            user=agent,
            entity_type="CallAttempt",
            entity_id=attempt.id,
            action="CALL_ATTEMPT_LOGGED",
            new_value={
                "attempt_number": attempt.attempt_number,
                "outcome": attempt.outcome,
                "lead": str(lead.id),
                "suggest_mark_lost": suggest_mark_lost,
            },
        )

        # Notify the lead owner when someone else logs an attempt on their lead.
        if lead.assigned_to and lead.assigned_to != agent:
            trigger_notification_event(
                event_type=NotificationEventType.CALL_ATTEMPT_LOGGED,
                recipient=lead.assigned_to,
                context={
                    "user_name": (
                        lead.assigned_to.get_full_name() or lead.assigned_to.username
                    ),
                    "employee_name": agent.get_full_name() or agent.username,
                    "lead_name": lead.name,
                    "attempt_number": attempt.attempt_number,
                    "outcome": attempt.outcome,
                },
            )

        logger.info(
            "Logged CallAttempt #%s for Lead %s (outcome=%s, suggest_mark_lost=%s)",
            attempt.attempt_number,
            lead.id,
            attempt.outcome,
            suggest_mark_lost,
        )
        return attempt, suggest_mark_lost


def validate_submission_data(template_version, form_data):
    """
    Validates submitted JSON data dictionary against TemplateVersion fields schema.
    Raises ValidationError if required fields are missing or select values are invalid.
    """
    errors = {}
    fields = template_version.fields.all()

    for field in fields:
        key = field.field_key
        val = form_data.get(key)

        # Check required fields
        if field.is_required and (
            val is None or val == "" or (isinstance(val, list) and not val)
        ):
            errors[key] = f"'{field.label}' is required."
            continue

        # Check select option choices
        if field.field_type == FieldType.SELECT and val is not None and val != "":
            if field.options and val not in field.options:
                errors[key] = (
                    f"Invalid choice '{val}'. Allowed choices are: {field.options}"
                )

    if errors:
        raise ValidationError(errors)

    return True


def sync_submission_to_lead(submission):
    """
    Writes basic-information form answers back onto the Lead so the data lives
    in the lead record (and therefore flows into Customer on conversion).

    Reserved field keys are mapped to Lead columns and applied
    *fill-if-blank only*: identity data already on the lead is never
    overwritten (it participates in customer-identity matching).

    Mapping:
        name / full_name   -> Lead.name          (only if blank)
        email              -> Lead.email         (only if blank)
        phone / mobile     -> Lead.phone         (only if blank)
        company_name / company -> Lead.company_name  (only if blank)
    """

    KEY_MAP = {
        "name": "name",
        "full_name": "name",
        "email": "email",
        "phone": "phone",
        "mobile": "phone",
        "company_name": "company_name",
        "company": "company_name",
    }

    lead = submission.lead
    if not lead:
        return []

    data = submission.data or {}
    updates = {}

    for raw_key, value in data.items():
        lead_field = KEY_MAP.get(str(raw_key).strip().lower())
        if not lead_field or value in (None, ""):
            continue

        current = getattr(lead, lead_field, None)
        if current in (None, ""):
            updates[lead_field] = str(value).strip()

    if updates:
        for field, value in updates.items():
            setattr(lead, field, value)
        lead.save(update_fields=list(updates.keys()) + ["updated_at"])
        logger.info(
            "Synced submission %s fields %s into Lead %s",
            submission.id,
            sorted(updates.keys()),
            lead.id,
        )

    return sorted(updates.keys())


def submit_call_form(
    lead_or_id,
    agent,
    template_version_or_id,
    form_data,
    call_attempt_or_id=None,
    notes="",
    quotation_or_id=None,
):
    """
    Validates payload against TemplateVersion schema, creates a FormSubmission,
    updates CallAttempt status, and freezes the TemplateVersion.

    ``quotation_or_id`` optionally links the submission to a Quotation
    (e.g. a "Quotation Discussion" call) without touching quotation state.
    """
    from customer_management.models import Lead, Quotation

    with transaction.atomic():
        if isinstance(lead_or_id, Lead):
            lead = lead_or_id
        else:
            lead = Lead.objects.get(pk=lead_or_id)

        if isinstance(template_version_or_id, TemplateVersion):
            template_version = template_version_or_id
        else:
            template_version = TemplateVersion.objects.get(pk=template_version_or_id)

        # Validate form_data against template schema
        validate_submission_data(template_version, form_data)

        call_attempt = None
        if call_attempt_or_id:
            if isinstance(call_attempt_or_id, CallAttempt):
                call_attempt = call_attempt_or_id
            else:
                call_attempt = CallAttempt.objects.get(pk=call_attempt_or_id)

        quotation = None
        if quotation_or_id:
            if isinstance(quotation_or_id, Quotation):
                quotation = quotation_or_id
            else:
                quotation = Quotation.objects.get(pk=quotation_or_id)

        submission = FormSubmission.objects.create(
            lead=lead,
            call_attempt=call_attempt,
            template_version=template_version,
            submitted_by=agent,
            data=form_data,
            notes=notes,
            quotation=quotation,
        )

        if call_attempt:
            call_attempt.is_form_submitted = True
            call_attempt.outcome = OutcomeChoice.COMPLETED
            call_attempt.save(update_fields=["is_form_submitted", "outcome"])

        # Index submission values into IndexedSubmissionValue table
        index_submission_values(submission)

        # Write basic-information answers back onto the Lead record so they
        # survive into Customer on conversion.
        sync_submission_to_lead(submission)

        # Process automated task trigger rules
        process_submission_task_triggers(submission)

        CRMService.create_audit_log(
            user=agent,
            entity_type="FormSubmission",
            entity_id=submission.id,
            action="FORM_SUBMISSION_COMPLETED",
            new_value={
                "lead": str(lead.id),
                "template_version": str(template_version.id),
                "quotation": str(quotation.id) if quotation else None,
            },
        )

        # Notify the lead owner when someone else completed a form on their lead.
        if lead.assigned_to and lead.assigned_to != agent:
            trigger_notification_event(
                event_type=NotificationEventType.FORM_SUBMISSION_COMPLETED,
                recipient=lead.assigned_to,
                context={
                    "user_name": (
                        lead.assigned_to.get_full_name() or lead.assigned_to.username
                    ),
                    "employee_name": agent.get_full_name() or agent.username,
                    "lead_name": lead.name,
                    "template_name": template_version.template.name,
                },
            )

        logger.info(
            "Created FormSubmission %s for Lead %s on TemplateVersion %s",
            submission.id,
            lead.id,
            template_version.id,
        )
        return submission


def create_trigger_rule(
    template_version,
    name,
    trigger_condition=ConditionChoice.ALWAYS,
    condition_field_key="",
    condition_value=None,
    task_title_template="Follow-up with {lead_name}",
    task_category=None,
    task_priority=None,
    due_days_offset=1,
    assignee_rule=AssigneeRuleChoice.CONDUCTING_AGENT,
    specific_assignee=None,
    create_reminder=True,
    reminder_minutes_before=30,
):
    """
    Creates a TaskTriggerRule for a TemplateVersion.
    """
    return TaskTriggerRule.objects.create(
        template_version=template_version,
        name=name,
        trigger_condition=trigger_condition,
        condition_field_key=condition_field_key,
        condition_value=condition_value or {},
        task_title_template=task_title_template,
        task_category=task_category,
        task_priority=task_priority,
        due_days_offset=due_days_offset,
        assignee_rule=assignee_rule,
        specific_assignee=specific_assignee,
        create_reminder=create_reminder,
        reminder_minutes_before=reminder_minutes_before,
    )


def evaluate_trigger_condition(rule, submission):
    """
    Evaluates whether a FormSubmission satisfies a TaskTriggerRule's condition.
    """
    cond = rule.trigger_condition
    data = submission.data or {}

    if cond == ConditionChoice.ALWAYS:
        return True

    if cond == ConditionChoice.FOLLOW_UP_REQUIRED:
        return bool(data.get("follow_up_required") or data.get("is_followup_required"))

    if cond == ConditionChoice.OUTCOME_MATCH:
        if submission.call_attempt:
            expected_outcome = rule.condition_value.get("outcome")
            return submission.call_attempt.outcome == expected_outcome
        return False

    if cond == ConditionChoice.FIELD_VALUE_MATCH:
        key = rule.condition_field_key
        if key and key in data:
            expected = rule.condition_value.get("match_value")
            return data[key] == expected
        return False

    return False


def process_submission_task_triggers(submission):
    """
    Evaluates active TaskTriggerRule items for submission's TemplateVersion
    and creates Task, Followup, and Reminder instances accordingly.
    """
    from Task.models import (
        Task,
        TaskStatus,
        TaskPriority,
        Reminder,
        ReminderType,
        ReminderStatus,
    )
    from FollowUp.models import Followup, FollowUpStatus, FollowUpTypes

    # Safety net: guarantee canonical master rows exist so auto-created tasks
    # never fail with IntegrityError on empty lookup tables.
    canonical = ensure_canonical_task_master_data()

    rules = submission.template_version.trigger_rules.filter(is_active=True)
    created_tasks = []

    for rule in rules:
        if evaluate_trigger_condition(rule, submission):
            # Resolve assignee
            if rule.assignee_rule == AssigneeRuleChoice.CONDUCTING_AGENT:
                assignee = submission.submitted_by
            elif rule.assignee_rule == AssigneeRuleChoice.LEAD_OWNER:
                assignee = submission.lead.assigned_to or submission.submitted_by
            elif rule.assignee_rule == AssigneeRuleChoice.SPECIFIC_USER:
                assignee = rule.specific_assignee or submission.submitted_by
            else:
                assignee = submission.submitted_by

            # Resolve title template
            lead_name = submission.lead.name if submission.lead else "Lead"
            stage_name = (
                submission.lead.current_stage.name
                if (submission.lead and submission.lead.current_stage)
                else "Stage"
            )
            template_name = submission.template_version.template.name
            title = rule.task_title_template.format(
                lead_name=lead_name,
                stage_name=stage_name,
                template_name=template_name,
            )

            # Resolve Category, Priority, Status (fall back to canonical rows
            # guaranteed by ensure_canonical_task_master_data above).
            category = rule.task_category or canonical["category_general"]
            priority = (
                rule.task_priority
                or TaskPriority.objects.filter(priority_name="High").first()
                or canonical["priority_high"]
            )
            status_pending = (
                TaskStatus.objects.filter(status_name="Pending").first()
                or canonical["status_pending"]
            )

            # Calculate due date: an explicit follow-up date captured in the
            # form always wins; otherwise default to the rule's day offset
            # (next-day by default) so the lead is called again even when the
            # agent does not pick a date.
            due_date = None
            follow_up_raw = (submission.data or {}).get("follow_up_date")
            if isinstance(follow_up_raw, str) and follow_up_raw.strip():
                parsed = dateparse.parse_datetime(follow_up_raw.strip())
                if parsed is None:
                    try:
                        only_date = dateparse.parse_date(follow_up_raw.strip())
                        if only_date:
                            parsed = datetime.combine(only_date, time(10, 0))
                    except (TypeError, ValueError):
                        parsed = None
                if parsed is not None:
                    if timezone.is_naive(parsed):
                        parsed = timezone.make_aware(parsed)
                    if parsed > timezone.now():
                        due_date = parsed

            if due_date is None:
                due_date = timezone.now() + timezone.timedelta(
                    days=rule.due_days_offset
                )

            task = Task.objects.create(
                assigned_to=assignee,
                created_by=submission.submitted_by,
                lead=submission.lead,
                form_submission=submission,
                task_title=title,
                description=f"Auto-generated task from CallForm submission on {template_name}. Notes: {submission.notes or ''}",
                due_date=due_date,
                status=status_pending,
                priority=priority,
                category=category,
            )
            created_tasks.append(task)

            # Notify the assignee that an auto-generated task was assigned to
            # them (same pattern as manual task creation in Task/views.py).
            trigger_notification_event(
                event_type=NotificationEventType.TASK_ASSIGNED,
                recipient=assignee,
                context={
                    "user_name": assignee.get_full_name() or assignee.username,
                    "employee_name": (
                        submission.submitted_by.get_full_name()
                        or submission.submitted_by.username
                    ),
                    "task_title": title,
                    "due_date": str(due_date),
                },
            )

            # Create Followup record if available
            fu_status = FollowUpStatus.objects.filter(
                is_active=True
            ).first() or FollowUpStatus.objects.create(status_name="Pending")
            fu_type = FollowUpTypes.objects.filter(
                is_active=True
            ).first() or FollowUpTypes.objects.create(type_name="Call Followup")
            Followup.objects.create(
                task_id=task,
                followup_status=fu_status,
                followup_type=fu_type,
                followup_date=due_date,
                decription=title,
                created_by=submission.submitted_by,
            )

            # Create Reminder record if requested
            if rule.create_reminder:
                reminder_type = ReminderType.objects.filter(
                    is_active=True
                ).first() or ReminderType.objects.create(type_name="Notification")
                reminder_status = ReminderStatus.objects.filter(
                    is_active=True
                ).first() or ReminderStatus.objects.create(status_name="Pending")
                reminder_time = due_date - timezone.timedelta(
                    minutes=rule.reminder_minutes_before
                )
                # Skip reminders that would already be in the past (e.g. a large
                # minutes_before offset on a near-term due date) so the cron job
                # does not fire them immediately.
                if reminder_time > timezone.now():
                    Reminder.objects.create(
                        task_id=task,
                        reminder_for=assignee,
                        reminder_type_id=reminder_type,
                        reminder_status_id=reminder_status,
                        reminder_datetime=reminder_time,
                        message=f"Reminder: {title}",
                        created_by=submission.submitted_by,
                    )

    return created_tasks


def get_submission_adhoc_fields(submission):
    """
    Returns a dictionary of keys present in submission.data that are NOT
    defined in the TemplateVersion's fields schema.
    """
    defined_keys = set(
        submission.template_version.fields.values_list("field_key", flat=True)
    )
    data = submission.data or {}
    return {k: v for k, v in data.items() if k not in defined_keys}


def filter_submissions_by_field_value(queryset, field_key, value):
    """
    Filters a FormSubmission queryset where JSON data contains field_key = value.
    """
    filter_kwargs = {f"data__{field_key}": value}
    return queryset.filter(**filter_kwargs)


def get_template_version_analytics(template_version_or_id):
    """
    Computes reporting metrics and response distributions for a TemplateVersion.
    """
    if isinstance(template_version_or_id, TemplateVersion):
        version = template_version_or_id
    else:
        version = TemplateVersion.objects.get(pk=template_version_or_id)

    submissions = FormSubmission.objects.filter(template_version=version)
    total_submissions = submissions.count()

    fields_analytics = {}
    adhoc_key_counts = {}

    schema_fields = list(version.fields.all())
    schema_keys = {f.field_key for f in schema_fields}

    for field in schema_fields:
        key = field.field_key
        values = []
        for sub in submissions:
            val = (sub.data or {}).get(key)
            if val is not None:
                values.append(val)

        analytics_data = {
            "label": field.label,
            "field_type": field.field_type,
            "response_count": len(values),
            "response_rate_pct": (
                round((len(values) / total_submissions * 100), 2)
                if total_submissions > 0
                else 0
            ),
        }

        if field.field_type == FieldType.SELECT:
            distribution = {}
            for v in values:
                str_v = str(v)
                distribution[str_v] = distribution.get(str_v, 0) + 1
            analytics_data["distribution"] = distribution
        elif field.field_type == FieldType.BOOLEAN:
            true_cnt = sum(1 for v in values if bool(v))
            analytics_data["boolean_counts"] = {
                "true": true_cnt,
                "false": len(values) - true_cnt,
            }
        elif field.field_type == FieldType.NUMBER:
            numeric_vals = [v for v in values if isinstance(v, (int, float))]
            if numeric_vals:
                analytics_data["numeric_stats"] = {
                    "min": min(numeric_vals),
                    "max": max(numeric_vals),
                    "avg": round(sum(numeric_vals) / len(numeric_vals), 2),
                }

        fields_analytics[key] = analytics_data

    # Count ad-hoc key occurrences
    for sub in submissions:
        data = sub.data or {}
        for k in data.keys():
            if k not in schema_keys:
                adhoc_key_counts[k] = adhoc_key_counts.get(k, 0) + 1

    return {
        "template_version_id": str(version.id),
        "version_label": version.version_label,
        "template_name": version.template.name,
        "total_submissions": total_submissions,
        "fields_analytics": fields_analytics,
        "adhoc_key_counts": adhoc_key_counts,
    }


def get_lead_timeline_feed(lead_or_id=None, account_id=None, contact_id=None):
    """
    Consolidates CallAttempts and FormSubmissions for a specific Lead,
    or across all leads under a CustomerAccount/CustomerContact into a unified feed.
    """
    from customer_management.models import Lead

    if account_id:
        leads_qs = Lead.objects.filter(customer_account_id=account_id)
        attempts = CallAttempt.objects.filter(lead__in=leads_qs).select_related(
            "agent", "lead"
        )
        submissions = FormSubmission.objects.filter(lead__in=leads_qs).select_related(
            "submitted_by", "template_version__template", "lead"
        )
        target_id = str(account_id)
        target_name = "Customer Account Portfolio Feed"
    elif contact_id:
        leads_qs = Lead.objects.filter(customer_contact_id=contact_id)
        attempts = CallAttempt.objects.filter(lead__in=leads_qs).select_related(
            "agent", "lead"
        )
        submissions = FormSubmission.objects.filter(lead__in=leads_qs).select_related(
            "submitted_by", "template_version__template", "lead"
        )
        target_id = str(contact_id)
        target_name = "Customer Contact Portfolio Feed"
    else:
        if isinstance(lead_or_id, Lead):
            lead = lead_or_id
        else:
            lead = Lead.objects.get(pk=lead_or_id)
        attempts = CallAttempt.objects.filter(lead=lead).select_related("agent", "lead")
        submissions = FormSubmission.objects.filter(lead=lead).select_related(
            "submitted_by", "template_version__template", "lead"
        )
        target_id = str(lead.id)
        target_name = lead.name

    timeline = []

    for att in attempts:
        timeline.append(
            {
                "id": str(att.id),
                "entry_type": "CALL_ATTEMPT",
                "timestamp": att.created_at.isoformat(),
                "actor": att.agent.username if att.agent else "System",
                "actor_id": str(att.agent.pk) if att.agent else None,
                "lead_id": str(att.lead.id),
                "lead_title": att.lead.name,
                "details": {
                    "attempt_number": att.attempt_number,
                    "outcome": att.outcome,
                    "duration_seconds": att.duration_seconds,
                    "is_form_submitted": att.is_form_submitted,
                    "notes": att.notes,
                },
            }
        )

    for sub in submissions:
        timeline.append(
            {
                "id": str(sub.id),
                "entry_type": "FORM_SUBMISSION",
                "timestamp": sub.created_at.isoformat(),
                "actor": sub.submitted_by.username if sub.submitted_by else "System",
                "actor_id": str(sub.submitted_by.pk) if sub.submitted_by else None,
                "lead_id": str(sub.lead.id),
                "lead_title": sub.lead.name,
                "details": {
                    "template_name": sub.template_version.template.name,
                    "version_label": sub.template_version.version_label,
                    "submission_data": sub.data,
                    "adhoc_fields": get_submission_adhoc_fields(sub),
                    "notes": sub.notes,
                },
            }
        )

    # Sort reverse-chronologically by timestamp
    timeline.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "target_id": target_id,
        "target_name": target_name,
        "total_events": len(timeline),
        "timeline": timeline,
    }


def ensure_canonical_task_master_data():
    """
    Ensures deterministic existence of canonical Task master rows:
    Status: Pending, Completed
    Priority: High
    Category: General
    """
    from Task.models import TaskStatus, TaskPriority, TaskCategory

    status_pending, _ = TaskStatus.objects.get_or_create(
        status_name="Pending", defaults={"is_active": True}
    )
    status_completed, _ = TaskStatus.objects.get_or_create(
        status_name="Completed", defaults={"is_active": True}
    )
    priority_high, _ = TaskPriority.objects.get_or_create(
        priority_name="High",
        defaults={"description": "High Priority", "is_active": True},
    )
    category_general, _ = TaskCategory.objects.get_or_create(
        category_name="General", defaults={"is_active": True}
    )

    return {
        "status_pending": status_pending,
        "status_completed": status_completed,
        "priority_high": priority_high,
        "category_general": category_general,
    }


def propose_adhoc_field(
    *,
    user,
    template_version,
    field_key,
    label,
    field_type=FieldType.TEXT,
    help_text=None,
    options=None,
):
    """
    Creates an AdhocFieldProposal for review by a Manager.
    """
    proposal = AdhocFieldProposal.objects.create(
        template_version=template_version,
        field_key=field_key.lower().strip(),
        label=label.strip(),
        field_type=field_type,
        help_text=help_text,
        options=options or [],
        status=ProposalStatus.PENDING,
        proposed_by=user,
    )

    CRMService.create_audit_log(
        user=user,
        entity_type="AdhocFieldProposal",
        entity_id=proposal.id,
        action="ADHOC_FIELD_PROPOSED",
        new_value={"label": proposal.label, "field_key": proposal.field_key},
    )

    trigger_notification_event(
        event_type=NotificationEventType.ADHOC_FIELD_PROPOSED,
        recipient=user,
        context={
            "user_name": user.get_full_name() or user.username,
            "proposal_id": str(proposal.id),
            "label": proposal.label,
        },
    )

    return proposal


@transaction.atomic
def review_adhoc_field(*, user, proposal, status, rejection_reason=None):
    """
    Manager reviews an AdhocFieldProposal (APPROVED or REJECTED).
    If approved, adds the field to the template version. If locked, creates a new version.
    """
    if proposal.status != ProposalStatus.PENDING:
        raise ValidationError("This proposal has already been reviewed.")

    if status not in [ProposalStatus.APPROVED, ProposalStatus.REJECTED]:
        raise ValidationError("Review status must be APPROVED or REJECTED.")

    proposal.status = status
    proposal.reviewed_by = user
    proposal.reviewed_at = timezone.now()
    if status == ProposalStatus.REJECTED:
        proposal.rejection_reason = rejection_reason
    proposal.save(
        update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason"]
    )

    if status == ProposalStatus.APPROVED:
        target_version = proposal.template_version
        if target_version.is_locked:
            target_version = clone_template_version(
                target_version,
                created_by=user,
                set_primary=True,
            )

        max_order = (
            target_version.fields.aggregate(models.Max("display_order"))[
                "display_order__max"
            ]
            or 0
        )
        TemplateField.objects.create(
            template_version=target_version,
            field_key=proposal.field_key,
            label=proposal.label,
            field_type=proposal.field_type,
            help_text=proposal.help_text,
            options=proposal.options,
            display_order=max_order + 1,
        )

    CRMService.create_audit_log(
        user=user,
        entity_type="AdhocFieldProposal",
        entity_id=proposal.id,
        action=(
            "ADHOC_FIELD_APPROVED"
            if status == ProposalStatus.APPROVED
            else "ADHOC_FIELD_REJECTED"
        ),
        new_value={"status": status, "reviewed_by": str(user.pk)},
    )

    return proposal


def index_submission_values(submission):
    """
    Indexes dynamic JSON field data from FormSubmission into IndexedSubmissionValue records.
    """
    data = submission.data or {}
    indexed_records = []

    for key, val in data.items():
        if val is None:
            continue

        value_text = None
        value_number = None
        value_date = None
        value_boolean = None

        if isinstance(val, bool):
            value_boolean = val
            value_text = str(val)
        elif isinstance(val, (int, float, Decimal)):
            value_number = Decimal(str(val))
            value_text = str(val)
        elif isinstance(val, str):
            value_text = val
            if len(val) == 10 and val[4] == "-" and val[7] == "-":
                try:
                    from datetime import datetime

                    value_date = datetime.strptime(val, "%Y-%m-%d").date()
                except ValueError:
                    pass
        else:
            value_text = str(val)

        rec, _ = IndexedSubmissionValue.objects.update_or_create(
            submission=submission,
            field_key=key,
            defaults={
                "value_text": value_text,
                "value_number": value_number,
                "value_date": value_date,
                "value_boolean": value_boolean,
            },
        )
        indexed_records.append(rec)

    return indexed_records
