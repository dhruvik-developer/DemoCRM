from django.contrib import admin
from .models import NotificationTemplate, Notification


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "event_type", "channel", "is_default", "is_active", "updated_at")
    list_filter = ("event_type", "channel", "is_default", "is_active")
    search_fields = ("name", "event_type", "message")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "event_type", "channel", "is_read", "read_at", "created_at")
    list_filter = ("event_type", "channel", "is_read", "created_at")
    search_fields = ("recipient__username", "recipient__email", "event_type", "message")
