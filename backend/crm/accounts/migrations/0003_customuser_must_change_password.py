# Generated for must_change_password feature (first-login password change enforcement).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_alter_customuser_phone_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="must_change_password",
            field=models.BooleanField(
                default=False,
                help_text="True when the user must change password on next login (first login after admin creation).",
            ),
        ),
    ]
