"""Django admin registration for core infrastructure models."""

from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "actor", "target_user", "outcome", "ip_address", "created_at")
    list_filter = ("action", "outcome")
    search_fields = ("actor__username", "target_user__username")
    readonly_fields = (
        "actor",
        "action",
        "target_user",
        "target_resource_type",
        "target_resource_id",
        "old_value",
        "new_value",
        "outcome",
        "ip_address",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
