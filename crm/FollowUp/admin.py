from django.contrib import admin
from .models import (
    FollowUpStatus,
    FollowUpTypes,
    Followup,
    ActivityType,
    ActivityAction,
    ActivityLog,
)

admin.site.register(FollowUpStatus)
admin.site.register(FollowUpTypes)
admin.site.register(Followup)
admin.site.register(ActivityType)
admin.site.register(ActivityAction)
admin.site.register(ActivityLog)
