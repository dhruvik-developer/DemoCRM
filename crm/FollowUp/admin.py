from django.contrib import admin
from .models import (
    FollowUpStatus,
    FollowUpTypes,
    Followup,
    FollowUpNote,
    ActivityType,
    ActivityAction,
    ActivityLog,
    NotificationType,
    NotificationTemplate,
    Notification,
)

admin.site.register(FollowUpStatus)
admin.site.register(FollowUpTypes)
admin.site.register(Followup)
admin.site.register(FollowUpNote)
admin.site.register(ActivityType)
admin.site.register(ActivityAction)
admin.site.register(ActivityLog)
admin.site.register(NotificationType)
admin.site.register(NotificationTemplate)
admin.site.register(Notification)
