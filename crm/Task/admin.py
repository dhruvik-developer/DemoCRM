from django.contrib import admin
from .models import (
    TaskStatus,
    TaskPriority,
    TaskCategory,
    Task,
    MeetingStatus,
    MeetingType,
    Meeting,
    MeetingParticipant,
    ReminderType,
    ReminderStatus,
    Reminder,
)

admin.site.register(TaskStatus)
admin.site.register(TaskPriority)
admin.site.register(TaskCategory)
admin.site.register(Task)
admin.site.register(MeetingStatus)
admin.site.register(MeetingType)
admin.site.register(Meeting)
admin.site.register(MeetingParticipant)
admin.site.register(ReminderType)
admin.site.register(ReminderStatus)
admin.site.register(Reminder)
