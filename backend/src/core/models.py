"""Core infrastructure models."""

from django.conf import settings
from django.db import models

# Re-export ImageAsset so Django discovers it under the 'core' app label.
from core.media.models import ImageAsset  # noqa: F401


class AuditAction(models.TextChoices):
    SUDO_GRANT = "SUDO_GRANT"
    SUDO_REVOKE = "SUDO_REVOKE"
    ROLE_CHANGE = "ROLE_CHANGE"
    USER_DELETE = "USER_DELETE"
    PASSWORD_RESET = "PASSWORD_RESET"
    SCORE_OVERRIDE = "SCORE_OVERRIDE"
    ARCHIVE = "ARCHIVE"
    RESTORE = "RESTORE"
    PURGE = "PURGE"
    IMAGE_UPLOAD = "IMAGE_UPLOAD"
    IMAGE_PROXY_UPLOAD = "IMAGE_PROXY_UPLOAD"
    IMAGE_DELETE = "IMAGE_DELETE"
    PKG_BUILD = "PKG_BUILD"
    PKG_DOWNLOAD = "PKG_DOWNLOAD"


class AuditOutcome(models.TextChoices):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs_as_actor",
    )
    action = models.CharField(max_length=32, choices=AuditAction.choices)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs_as_target",
    )
    target_resource_type = models.CharField(max_length=64, null=True, blank=True)
    target_resource_id = models.IntegerField(null=True, blank=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    outcome = models.CharField(
        max_length=16, choices=AuditOutcome.choices, default=AuditOutcome.PENDING
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} by {self.actor_id} at {self.created_at}"
