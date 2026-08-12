from django.contrib import admin

from .models import (
    Activity,
    AuditLog,
    Customer,
    Lead,
    LeadSource,
    Pipeline,
    PipelineStage,
)


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "created_by",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "created_by",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(PipelineStage)
class PipelineStageAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "pipeline",
        "display_order",
        "is_active",
        "created_at",
    )
    list_filter = ("pipeline", "is_active")
    search_fields = ("name", "description")
    ordering = ("pipeline", "display_order")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "company_name",
        "assigned_to",
        "pipeline",
        "current_stage",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
        "pipeline",
        "current_stage",
    )
    search_fields = (
        "name",
        "email",
        "phone",
        "company_name",
    )
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "phone",
        "company_name",
        "lead",
        "created_at",
    )
    search_fields = (
        "name",
        "email",
        "phone",
        "company_name",
    )
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "activity_type",
        "lead",
        "customer",
        "created_by",
        "outcome",
        "follow_up_required",
        "follow_up_date",
        "created_at",
    )
    list_filter = (
        "activity_type",
        "follow_up_required",
    )
    search_fields = (
        "outcome",
        "notes",
    )
    readonly_fields = ("id", "created_at", "updated_at")


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