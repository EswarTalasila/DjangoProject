"""Admin registrations for accounts models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    OAuthAccount,
    PasswordResetCode,
    PasswordResetRequest,
    RegistrationCode,
    ResearcherProfile,
    StudentProfile,
    SudoGrant,
    TeacherProfile,
    User,
    UserRole,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admin configuration for user accounts."""

    list_display = ("username", "email", "name", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff")
    ordering = ("username",)
    search_fields = ("username", "email", "name")

    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Profile", {"fields": ("name",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """Admin configuration for user roles."""

    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username", "user__name")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Admin configuration for student profiles."""

    list_display = ("user", "consent", "created_by", "created_at")
    search_fields = ("user__username", "user__name")
    list_filter = ("consent",)


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    """Admin configuration for teacher profiles."""

    list_display = ("user", "created_at")
    search_fields = ("user__username", "user__name")


@admin.register(ResearcherProfile)
class ResearcherProfileAdmin(admin.ModelAdmin):
    """Admin configuration for researcher profiles."""

    list_display = ("user", "created_at")
    search_fields = ("user__username", "user__name")


@admin.register(SudoGrant)
class SudoGrantAdmin(admin.ModelAdmin):
    """Admin configuration for sudo grants."""

    list_display = ("id", "user", "granted_by", "can_grant_sudo", "granted_at")
    list_filter = ("can_grant_sudo",)
    search_fields = ("user__username", "granted_by__username")


@admin.register(OAuthAccount)
class OAuthAccountAdmin(admin.ModelAdmin):
    """Admin configuration for linked OAuth accounts."""

    list_display = ("provider", "email", "user", "created_at", "last_login_at")
    search_fields = ("email", "subject", "user__username")
    list_filter = ("provider", "email_verified")


@admin.register(RegistrationCode)
class RegistrationCodeAdmin(admin.ModelAdmin):
    """Admin configuration for invite/registration codes."""

    list_display = (
        "code_prefix",
        "code_type",
        "course",
        "is_active",
        "times_used",
        "max_uses",
        "expires_at",
        "archived_at",
    )
    list_filter = ("code_type", "is_active", "archived_at")
    search_fields = ("code_prefix", "course__name", "created_by__username")


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    """Admin configuration for password reset requests."""

    list_display = ("id", "user", "status", "requested_at", "expires_at", "reviewed_by")
    list_filter = ("status",)
    search_fields = ("identifier", "user__username")


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    """Admin configuration for one-time password reset codes."""

    list_display = ("id", "request", "expires_at", "used_at", "created_at")
    search_fields = ("request__identifier", "request__user__username")
