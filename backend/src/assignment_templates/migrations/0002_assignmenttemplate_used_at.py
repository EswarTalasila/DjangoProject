from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assignment_templates", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignmenttemplate",
            name="used_at",
            field=models.DateTimeField(
                blank=True,
                help_text="First time an assignment was created from this template.",
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name="assignmenttemplate",
            index=models.Index(fields=["used_at"], name="idx_atmpl_used_at"),
        ),
    ]
