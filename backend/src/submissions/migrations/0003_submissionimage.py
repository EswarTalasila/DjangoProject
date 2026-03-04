"""FR-15: Add SubmissionImage model for image uploads."""

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("submissions", "0002_alter_answer_answer_type_delete_moodmeteranswer"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubmissionImage",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("storage_key", models.CharField(max_length=512, unique=True)),
                ("original_filename", models.CharField(max_length=255)),
                ("mime_type", models.CharField(max_length=64)),
                ("size_bytes", models.PositiveIntegerField()),
                ("sha256_hash", models.CharField(max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING_SCAN", "Pending Scan"),
                            ("READY", "Ready"),
                            ("REJECTED", "Rejected"),
                            ("DELETED", "Deleted"),
                        ],
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "submission",
                    models.ForeignKey(
                        db_column="submission_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="submissions.submission",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        db_column="uploaded_by_user_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="uploaded_images",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "submission_owner",
                    models.ForeignKey(
                        db_column="submission_owner_user_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owned_submission_images",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "submission_image",
            },
        ),
        migrations.AddIndex(
            model_name="submissionimage",
            index=models.Index(
                fields=["submission", "status"],
                name="idx_subimg_sub_status",
            ),
        ),
        migrations.AddConstraint(
            model_name="submissionimage",
            constraint=models.CheckConstraint(
                check=models.Q(("size_bytes__gt", 0)),
                name="ck_subimg_size_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="submissionimage",
            constraint=models.UniqueConstraint(
                condition=~models.Q(("status", "DELETED")),
                fields=("submission", "sha256_hash"),
                name="uq_subimg_hash_active",
            ),
        ),
    ]
