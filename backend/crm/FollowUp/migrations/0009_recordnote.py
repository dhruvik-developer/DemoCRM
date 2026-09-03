from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("FollowUp", "0008_merge_branches"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecordNote",
            fields=[
                ("note_id", models.AutoField(primary_key=True, serialize=False)),
                ("entity_type", models.CharField(choices=[("task", "Task"), ("followup", "Follow-up"), ("meeting", "Meeting")], max_length=20)),
                ("entity_id", models.PositiveIntegerField()),
                ("body", models.TextField(max_length=5000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="record_notes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(model_name="recordnote", index=models.Index(fields=["entity_type", "entity_id"], name="FollowUp_re_entity__a9a81d_idx")),
    ]
