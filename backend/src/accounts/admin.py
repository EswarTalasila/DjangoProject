"""Admin registrations for accounts models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import OAuthAccount, StudentProfile, TeacherProfile, User, UserRole


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admin configuration for user accounts."""

    list_display = ("username", "name", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff")
    ordering = ("username",)
    search_fields = ("username", "name")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
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


@admin.register(OAuthAccount)
class OAuthAccountAdmin(admin.ModelAdmin):
    """Admin configuration for linked OAuth accounts."""

    list_display = ("provider", "email", "user", "created_at", "last_login_at")
    search_fields = ("email", "subject", "user__username")
    list_filter = ("provider", "email_verified")
