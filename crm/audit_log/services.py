"""
Shared logging helpers for the whole CRM.

1. log_audit()      -> writes a row into the `audit_log` table (AuditLog model).
2. log_activity()   -> writes a row into the `activity` table (Activity model).

Follows the same pattern as customer_management.CRMService.create_audit_log
but safe to call from any app (Task, FollowUp, Meeting, Reminder).

NOTE: AuditLog.entity_id is a UUIDField while Task / FollowUp / Meeting /
Reminder use integer AutoField PKs. Integer (or non-UUID string) IDs are
converted to a deterministic UUID via uuid5, exactly as suggested in the
AuditLog model docstring.

Both helpers never raise: a logging failure must not break the main request.
Errors are logged instead.
"""

import logging
import uuid

from audit_log.models import Activity, AuditLog

logger = logging.getLogger(__name__)

# Fixed namespace used to derive deterministic UUIDs from integer PKs.
AUDIT_LOG_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "democrm.local.audit-log")


def _to_uuid(entity_type, entity_id):
    """
    Convert an entity PK to a UUID suitable for AuditLog.entity_id.
    Real UUIDs are kept as-is; anything else gets a deterministic uuid5.
    """
    if isinstance(entity_id, uuid.UUID):
        return entity_id

    if isinstance(entity_id, str):
        try:
            return uuid.UUID(entity_id)
        except (ValueError, AttributeError, TypeError):
            pass

    return uuid.uuid5(AUDIT_LOG_NAMESPACE, f"{entity_type}:{entity_id}")


def log_audit(
    *,
    user,
    entity_type,
    entity_id,
    action,
    old_value=None,
    new_value=None,
    metadata=None,
):
    """
    Save an audit trail entry in the audit_log table.

    :param user: user performing the action (request.user)
    :param entity_type: logical entity name e.g. "Task", "FollowUp", "Meeting"
    :param entity_id: PK of the entity (int, str or UUID - auto converted)
    :param action: action name e.g. "TASK_CREATED"
    :param old_value / new_value / metadata: optional JSON dicts
    """
    try:
        return AuditLog.objects.create(
            user=user,
            entity_type=entity_type,
            entity_id=_to_uuid(entity_type, entity_id),
            action=action,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata,
        )
    except Exception:
        logger.exception(
            "Failed to write audit log: entity_type=%s entity_id=%s action=%s",
            entity_type,
            entity_id,
            action,
        )
        return None


def _is_employee(user):
    """
    True when the user is a normal Employee
    (i.e. NOT superuser / admin / manager).
    """
    if user is None or getattr(user, "is_superuser", False):
        return False

    role = getattr(user, "role", None)
    if role is None:
        return True

    role_name = getattr(role, "rolename", "").strip().lower()
    return role_name not in ["admin", "manager"]


def log_activity(
    *,
    user,
    activity_type,
    outcome,
    notes=None,
    lead=None,
    customer=None,
    quotation=None,
    follow_up_required=False,
    follow_up_date=None,
):
    """
    Save an activity entry in the activity table.

    An Activity must belong to either a Lead or a Customer (same rule as the
    Activity model). If neither is supplied the entry is skipped.

    :param user: user performing the activity (request.user)
    :param activity_type: Activity.ActivityType value
    :param outcome: short summary of what happened
    """
    try:
        if lead is None and customer is None:
            logger.debug(
                "Activity skipped (no lead/customer): type=%s outcome=%s",
                activity_type,
                outcome,
            )
            return None

        return Activity.objects.create(
            created_by=user,
            activity_type=activity_type,
            outcome=outcome[:255],
            notes=notes,
            lead=lead,
            customer=customer,
            quotation=quotation,
            follow_up_required=follow_up_required,
            follow_up_date=follow_up_date,
        )
    except Exception:
        logger.exception(
            "Failed to write activity log: type=%s outcome=%s",
            activity_type,
            outcome,
        )
        return None
