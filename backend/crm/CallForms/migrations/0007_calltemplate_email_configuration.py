from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("CallForms", "0006_alter_callattempt_options_and_more")]

    operations = [
        migrations.AddField(
            model_name="calltemplate",
            name="email_configuration",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
