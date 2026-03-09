from django.db import migrations, models


CROSS = "CROSS_COURSE_SUBMISSIONS"


def remove_cross_course_bindings(apps, schema_editor):
    PackageNode = apps.get_model("packages", "PackageNode")
    DataSnapshot = apps.get_model("packages", "DataSnapshot")

    PackageNode.objects.filter(dataset_binding=CROSS).delete()
    DataSnapshot.objects.filter(dataset_binding=CROSS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("packages", "0003_add_workspace_delete_audit_action"),
    ]

    operations = [
        migrations.RunPython(remove_cross_course_bindings, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="datasnapshot",
            name="dataset_binding",
            field=models.CharField(
                choices=[
                    ("ROSTER", "Roster"),
                    ("COURSE_SUBMISSIONS", "Course Submissions"),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="packagenode",
            name="dataset_binding",
            field=models.CharField(
                blank=True,
                choices=[
                    ("ROSTER", "Roster"),
                    ("COURSE_SUBMISSIONS", "Course Submissions"),
                ],
                max_length=32,
                null=True,
            ),
        ),
    ]
