from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_remove_registrationcode_idx_registration_code_hash"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="registrationcode",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        code_type="STUDENT",
                        course_id__isnull=False,
                    )
                    | (
                        ~models.Q(code_type="STUDENT")
                        & models.Q(course_id__isnull=True)
                    )
                ),
                name="ck_registration_code_course_binding",
            ),
        ),
    ]
