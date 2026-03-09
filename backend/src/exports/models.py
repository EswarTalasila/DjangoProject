from django.conf import settings
from django.db import models


class ExportAuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="export_audit_logs",
    )
    export_type = models.CharField(max_length=32)  # "roster" or "submissions"
    scope_course = models.ForeignKey(
        "courses.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="export_audit_logs",
    )
    filters = models.JSONField(default=dict)
    identifiable = models.BooleanField()
    row_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "export_audit_logs"
        ordering = ["-created_at"]
