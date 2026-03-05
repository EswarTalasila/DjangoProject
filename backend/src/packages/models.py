"""FR-16 Packaging Workspace domain models."""

from django.conf import settings
from django.db import models


class WorkspaceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SEALED = "SEALED", "Sealed"


class NodeType(models.TextChoices):
    FOLDER = "FOLDER", "Folder"
    FILE = "FILE", "File"


class DatasetBinding(models.TextChoices):
    ROSTER = "ROSTER", "Roster"
    COURSE_SUBMISSIONS = "COURSE_SUBMISSIONS", "Course Submissions"


class BuildStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class SnapshotStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    READY = "READY", "Ready"
    FAILED = "FAILED", "Failed"
    EXPIRED = "EXPIRED", "Expired"


class NodeSourceType(models.TextChoices):
    LIVE = "LIVE", "Live"
    SNAPSHOT = "SNAPSHOT", "Snapshot"


class PackageWorkspace(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16, choices=WorkspaceStatus.choices, default=WorkspaceStatus.DRAFT
    )
    scope_course = models.ForeignKey(
        "courses.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="package_workspaces",
        db_column="scope_course_id",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="package_workspaces",
        db_column="created_by_id",
    )
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "package_workspaces"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Workspace {self.id}: {self.name}"


class PackageNode(models.Model):
    workspace = models.ForeignKey(
        PackageWorkspace,
        on_delete=models.CASCADE,
        related_name="nodes",
        db_column="workspace_id",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        db_column="parent_id",
    )
    node_type = models.CharField(max_length=8, choices=NodeType.choices)
    label = models.CharField(max_length=255)
    order_index = models.PositiveIntegerField(default=0)
    # File-node binding fields
    dataset_binding = models.CharField(
        max_length=32, choices=DatasetBinding.choices, null=True, blank=True
    )
    binding_course_id = models.IntegerField(null=True, blank=True)
    filters = models.JSONField(null=True, blank=True)
    identifiable = models.BooleanField(default=False)
    include_answers = models.BooleanField(default=False)
    source_type = models.CharField(
        max_length=16, choices=NodeSourceType.choices, default=NodeSourceType.LIVE
    )
    snapshot = models.ForeignKey(
        "DataSnapshot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nodes",
        db_column="snapshot_id",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "package_nodes"
        ordering = ["order_index", "id"]

    def __str__(self):
        return f"Node {self.id}: {self.label} ({self.node_type})"


class PackageBuildJob(models.Model):
    workspace = models.ForeignKey(
        PackageWorkspace,
        on_delete=models.CASCADE,
        related_name="build_jobs",
        db_column="workspace_id",
    )
    status = models.CharField(
        max_length=16, choices=BuildStatus.choices, default=BuildStatus.QUEUED
    )
    strict_mode = models.BooleanField(default=True)
    snapshot_id = models.IntegerField(null=True, blank=True)
    mode = models.CharField(max_length=8, default="live")  # "live" or "snapshot"
    error_message = models.TextField(blank=True, default="")
    warnings = models.JSONField(default=list)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="package_build_jobs",
        db_column="created_by_id",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "package_build_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Build {self.id}: {self.status}"


class PackageArtifact(models.Model):
    build_job = models.OneToOneField(
        PackageBuildJob,
        on_delete=models.CASCADE,
        related_name="artifact",
        db_column="build_job_id",
    )
    file_path = models.CharField(max_length=512)
    file_size = models.BigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64, blank=True, default="")
    manifest = models.JSONField(default=dict)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "package_artifacts"

    def __str__(self):
        return f"Artifact {self.id} for Build {self.build_job_id}"


class DataSnapshot(models.Model):
    workspace = models.ForeignKey(
        PackageWorkspace,
        on_delete=models.CASCADE,
        related_name="snapshots",
        db_column="workspace_id",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="data_snapshots",
        db_column="created_by_id",
    )
    dataset_binding = models.CharField(max_length=32, choices=DatasetBinding.choices)
    scope_course_id = models.IntegerField(null=True, blank=True)
    filters = models.JSONField(null=True, blank=True)
    include_answers = models.BooleanField(default=False)
    identifiable = models.BooleanField(default=False)
    storage_key = models.CharField(max_length=512, blank=True, default="")
    row_count = models.IntegerField(default=0)
    file_size = models.BigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(
        max_length=16, choices=SnapshotStatus.choices, default=SnapshotStatus.QUEUED
    )
    error_message = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "data_snapshots"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"], name="idx_snap_ws_status"),
            models.Index(fields=["created_by", "created_at"], name="idx_snap_creator"),
            models.Index(fields=["expires_at"], name="idx_snap_expires"),
        ]

    def __str__(self):
        return f"Snapshot {self.id}: {self.dataset_binding} ({self.status})"


class PkgAuditAction(models.TextChoices):
    WORKSPACE_CREATE = "WORKSPACE_CREATE"
    WORKSPACE_UPDATE = "WORKSPACE_UPDATE"
    WORKSPACE_DELETE = "WORKSPACE_DELETE"
    NODE_ADD = "NODE_ADD"
    NODE_UPDATE = "NODE_UPDATE"
    NODE_DELETE = "NODE_DELETE"
    NODE_REORDER = "NODE_REORDER"
    VALIDATE = "VALIDATE"
    BUILD = "BUILD"
    DOWNLOAD = "DOWNLOAD"
    SNAPSHOT_CREATE = "SNAPSHOT_CREATE"
    SNAPSHOT_EXPIRE = "SNAPSHOT_EXPIRE"


class PkgAuditOutcome(models.TextChoices):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"


class PackageAuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="package_audit_logs",
    )
    action = models.CharField(max_length=32, choices=PkgAuditAction.choices)
    workspace = models.ForeignKey(
        PackageWorkspace,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        db_column="workspace_id",
    )
    scope = models.CharField(max_length=64, blank=True, default="")
    metadata = models.JSONField(default=dict)
    outcome = models.CharField(
        max_length=16, choices=PkgAuditOutcome.choices, default=PkgAuditOutcome.SUCCESS
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "package_audit_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} by {self.actor_id} at {self.created_at}"
