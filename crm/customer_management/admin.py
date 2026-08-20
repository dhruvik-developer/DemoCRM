from django.contrib import admin

from audit_log.models import Activity, AuditLog

from .models import (
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


from .models import Quotation, QuotationVersion, QuotationLineItem, QuotationApproval


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = (
        "quotation_number",
        "lead",
        "customer",
        "status",
        "current_version",
        "accepted_version",
        "created_by",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("quotation_number",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(QuotationVersion)
class QuotationVersionAdmin(admin.ModelAdmin):
    list_display = (
        "quotation",
        "version_number",
        "status",
        "total_amount",
        "approved_at",
        "sent_at",
        "sent_to",
        "accepted_at",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("quotation__quotation_number", "sent_to", "revision_reason")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(QuotationLineItem)
class QuotationLineItemAdmin(admin.ModelAdmin):
    list_display = (
        "version",
        "description",
        "quantity",
        "unit_price",
        "amount",
        "created_at",
    )
    readonly_fields = ("id", "created_at")


@admin.register(QuotationApproval)
class QuotationApprovalAdmin(admin.ModelAdmin):
    list_display = (
        "version",
        "submitted_by",
        "reviewed_by",
        "decision",
        "submitted_at",
        "reviewed_at",
    )
    list_filter = ("decision",)
    readonly_fields = ("id", "submitted_at")
