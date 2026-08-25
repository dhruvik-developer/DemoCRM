from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "action",
        "entity_type",
        "entity_id",
        "user",
        "created_at",
    )
    list_filter = (
        "action",
        "entity_type",
    )
    search_fields = (
        "entity_type",
        "action",
    )
    readonly_fields = (
        "id",
        "user",
        "entity_type",
        "entity_id",
        "action",
        "old_value",
        "new_value",
        "metadata",
        "created_at",
    )
