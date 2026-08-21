from django.contrib import admin
from .models import (
    FollowUpStatus,
    FollowUpTypes,
    Followup,
    FollowUpNote,
)

admin.site.register(FollowUpStatus)
admin.site.register(FollowUpTypes)
admin.site.register(Followup)
admin.site.register(FollowUpNote)
