"""Management command to ensure admin user exists on startup."""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


User = get_user_model()


class Command(BaseCommand):
    """Ensure admin user exists from environment variables."""

    help = "Create admin user from ADMIN_EMAIL/ADMIN_PASSWORD env vars if not exists."

    def handle(self, *args, **options):
        """Create admin user if not exists."""
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.environ.get("ADMIN_PASSWORD", "change-me")
        admin_name = os.environ.get("ADMIN_USERNAME", "Admin")

        user = User.objects.filter(username__iexact=admin_email).first()
        if user:
            self.stdout.write(f"Admin user already exists: {admin_email}")
            return

        user = User.objects.create_user(
            username=admin_email,
            name=admin_name,
            password=admin_password,
        )
        user.is_staff=True
        user.is_superuser=True
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Created admin user: {admin_email}"))
