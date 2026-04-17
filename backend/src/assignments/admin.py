"""Admin registrations for assignments models."""

from django.contrib import admin

from .models import Assignment


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    """Admin configuration for assignments."""

    list_display = ("id", "assignment_template", "audience_type", "course", "open_at", "due_at")
    list_filter = ("audience_type",)
    search_fields = ("assignment_template__title",)
