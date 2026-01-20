"""Admin registrations for courses models."""

from django.contrib import admin

from .models import Course, Enrollment


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Admin configuration for courses."""

    list_display = ("name", "teacher_profile", "created_at")
    search_fields = ("name",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """Admin configuration for enrollments."""

    list_display = ("course", "student_profile", "status", "enrolled_at")
    list_filter = ("status",)
    search_fields = ("course__name", "student_profile__user__username")
