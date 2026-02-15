from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_registrationcode_hash_storage"),
    ]

    operations = [
        migrations.AddField(
            model_name="registrationcode",
            name="metadata",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
