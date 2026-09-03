from django.db import migrations


def seed_custom_meeting_type(apps, schema_editor):
    MeetingType = apps.get_model("Task", "MeetingType")
    MeetingType.objects.update_or_create(
        meeting_type_id=3,
        defaults={"type_name": "Custom", "is_active": True},
    )


class Migration(migrations.Migration):
    dependencies = [("Task", "0017_meeting_uq_meeting_task_date_time")]

    operations = [migrations.RunPython(seed_custom_meeting_type, migrations.RunPython.noop)]
