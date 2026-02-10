"""Management command to seed E2E users and roles."""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import Role
from accounts.services import ensure_profiles_for_role, set_single_role

User = get_user_model()


class Command(BaseCommand):
    """Seed deterministic E2E test fixtures."""

    help = "Seed baseline E2E users for Playwright workflows."

    def add_arguments(self, parser):
        """Register CLI arguments for the seed command."""
        parser.add_argument(
            "--force-password",
            action="store_true",
            help="Reset passwords for existing users to the provided env values.",
        )

    def handle(self, *args, **options):
        """Seed baseline users for E2E workflows."""
        force_password = options.get("force_password", False)

        admin_username = os.environ.get("E2E_ADMIN_USERNAME") or os.environ.get(
            "ADMIN_EMAIL", "admin@example.com"
        )
        admin_password = os.environ.get("E2E_ADMIN_PASSWORD") or os.environ.get(
            "ADMIN_PASSWORD", "change-me"
        )
        admin_name = os.environ.get("E2E_ADMIN_NAME") or os.environ.get("ADMIN_USERNAME", "Admin")

        teacher_username = os.environ.get("E2E_TEACHER_USERNAME")
        teacher_password = os.environ.get("E2E_TEACHER_PASSWORD", "teacherpass")

        student_username = os.environ.get("E2E_STUDENT_USERNAME")
        student_password = os.environ.get("E2E_STUDENT_PASSWORD", "studentpass")

        self._ensure_admin(admin_username, admin_name, admin_password, force_password)

        if teacher_username:
            self._ensure_user(
                teacher_username,
                "Teacher",
                teacher_password,
                Role.TEACHER,
                force_password,
            )

        if student_username:
            self._ensure_user(
                student_username,
                "Student",
                student_password,
                Role.STUDENT,
                force_password,
            )

        self.stdout.write(self.style.SUCCESS("E2E seed completed"))

    def _ensure_admin(self, username, name, password, force_password):
        """Create or update an admin user (is_staff, no user role)."""
        user = User.objects.filter(username__iexact=username).first()
        if user:
            updated = False
            if user.name != name:
                user.name = name
                updated = True
            if not user.is_staff:
                user.is_staff = True
                user.is_superuser = True
                updated = True
            if password and force_password:
                user.set_password(password)
                updated = True
            if updated:
                user.save()
            self.stdout.write(f"Updated admin user: {username}")
            return

        user = User.objects.create_user(username=username, name=name, password=password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.stdout.write(f"Created admin user: {username}")

    def _ensure_user(self, username, name, password, role, force_password):
        """Create or update a user with the requested role."""
        user = User.objects.filter(username__iexact=username).first()
        if user:
            updated = False
            if user.name != name:
                user.name = name
                updated = True
            if password and force_password:
                user.set_password(password)
                updated = True
            if updated:
                user.save()
            set_single_role(user, role)
            ensure_profiles_for_role(user, role, creator=user)
            self.stdout.write(f"Updated {role} user: {username}")
            return

        user = User.objects.create_user(username=username, name=name, password=password)
        set_single_role(user, role)
        ensure_profiles_for_role(user, role, creator=user)
        self.stdout.write(f"Created {role} user: {username}")
