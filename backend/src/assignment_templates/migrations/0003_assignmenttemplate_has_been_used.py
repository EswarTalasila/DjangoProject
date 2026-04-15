from django.db import migrations, models


def backfill_has_been_used(apps, schema_editor):
    """Mark templates as used when existing rows already imply historical usage."""
    AssignmentTemplate = apps.get_model("assignment_templates", "AssignmentTemplate")
    Assignment = apps.get_model("assignments", "Assignment")

    used_template_ids = set(
        Assignment.objects.values_list("assignment_template_id", flat=True).distinct()
    )

    AssignmentTemplate.objects.filter(used_at__isnull=False).update(has_been_used=True)
    if used_template_ids:
        AssignmentTemplate.objects.filter(id__in=used_template_ids).update(has_been_used=True)


def noop_reverse(apps, schema_editor):
    """Usage history is intentionally non-reversible."""


class Migration(migrations.Migration):
    dependencies = [
        ("assignment_templates", "0002_assignmenttemplate_used_at"),
        ("assignments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignmenttemplate",
            name="has_been_used",
            field=models.BooleanField(
                default=False,
                help_text="Whether any assignment has ever been created from this template.",
            ),
        ),
        migrations.AddIndex(
            model_name="assignmenttemplate",
            index=models.Index(fields=["has_been_used"], name="idx_atmpl_used_flag"),
        ),
        migrations.RunPython(backfill_has_been_used, noop_reverse),
    ]
