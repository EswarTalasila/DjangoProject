"""Django admin registration for FR-16 package models."""

from django.contrib import admin

from .models import (
    PackageArtifact,
    PackageAuditLog,
    PackageBuildJob,
    PackageNode,
    PackageWorkspace,
)


@admin.register(PackageWorkspace)
class PackageWorkspaceAdmin(admin.ModelAdmin):
    """Admin view for PackageWorkspace with status filtering and name search."""

    list_display = ("id", "name", "status", "created_by", "created_at")
    list_filter = ("status",)
    search_fields = ("name",)


@admin.register(PackageNode)
class PackageNodeAdmin(admin.ModelAdmin):
    """Admin view for PackageNode with node-type filtering."""

    list_display = ("id", "workspace", "label", "node_type", "parent")
    list_filter = ("node_type",)


@admin.register(PackageBuildJob)
class PackageBuildJobAdmin(admin.ModelAdmin):
    """Admin view for PackageBuildJob with status and mode filtering."""

    list_display = ("id", "workspace", "status", "mode", "created_by", "created_at")
    list_filter = ("status", "mode")


admin.site.register(PackageArtifact)
admin.site.register(PackageAuditLog)
