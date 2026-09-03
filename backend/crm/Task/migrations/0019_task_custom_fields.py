from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("Task", "0018_seed_custom_meeting_type")]

    operations = [
        migrations.AddField(
            model_name="task",
            name="custom_fields",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="User-defined task field definitions and values.",
            ),
        ),
    ]
