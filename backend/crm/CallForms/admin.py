from django.contrib import admin
from .models import (
    CallTemplate,
    FormFieldMapping,
    TemplateVersion,
    TemplateField,
    PipelineStageActivity,
    CallAttempt,
    FormSubmission,
)


@admin.register(CallTemplate)
class CallTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_by", "created_at")
    search_fields = ("name", "description")
    list_filter = ("is_active",)


@admin.register(TemplateVersion)
class TemplateVersionAdmin(admin.ModelAdmin):
    list_display = (
        "template",
        "version_number",
        "version_label",
        "is_primary",
        "is_active",
        "created_at",
    )
    list_filter = ("is_primary", "is_active")


@admin.register(TemplateField)
class TemplateFieldAdmin(admin.ModelAdmin):
    list_display = (
        "template_version",
        "field_key",
        "label",
        "field_type",
        "is_required",
        "display_order",
    )
    list_filter = ("field_type", "is_required")
    search_fields = ("field_key", "label")


@admin.register(PipelineStageActivity)
class PipelineStageActivityAdmin(admin.ModelAdmin):
    list_display = (
        "stage",
        "name",
        "activity_type",
        "form_type",
        "call_template",
        "is_primary",
        "is_active",
        "auto_create_followup",
        "followup_offset_days",
    )
    list_filter = (
        "activity_type",
        "form_type",
        "is_primary",
        "is_active",
        "auto_create_followup",
    )
    search_fields = ("name",)
    list_editable = ("auto_create_followup", "followup_offset_days")


@admin.register(CallAttempt)
class CallAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "lead",
        "attempt_number",
        "outcome",
        "agent",
        "is_form_submitted",
        "created_at",
    )
    list_filter = ("outcome", "is_form_submitted")


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ("lead", "template_version", "submitted_by", "created_at")
    search_fields = ("lead__name",)


@admin.register(FormFieldMapping)
class FormFieldMappingAdmin(admin.ModelAdmin):
    list_display = ("template", "field_key", "target_model", "target_field")
    list_filter = ("target_model",)
    search_fields = ("field_key", "target_field")
