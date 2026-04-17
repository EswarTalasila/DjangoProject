from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assignments", "0004_assignmentteachercriterionlevel"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="template_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
