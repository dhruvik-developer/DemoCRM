import logging

from .models import AuditLog

logger = logging.getLogger(__name__)


class AuditLogService:
    @staticmethod
    def create(
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
