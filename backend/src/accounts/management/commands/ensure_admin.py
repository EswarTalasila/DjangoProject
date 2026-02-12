"""Management command to ensure admin user exists on startup."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from config.env import env

User = get_user_model()


class Command(BaseCommand):
    """Ensure admin user exists from environment variables."""

    help = "Create admin user from ADMIN_EMAIL/ADMIN_PASSWORD env vars if not exists."

    def handle(self, *args, **options):
        """Create or reconcile startup admin account."""
        admin_email = env.admin_email.strip()
        admin_password = env.admin_password
        admin_name = env.admin_username.strip() or "Admin"

        if env.is_production:
            self._validate_production_admin_config(admin_email, admin_password)

        user = User.objects.filter(username__iexact=admin_email).first()
        if user:
            updated = False
            if user.name != admin_name:
                user.name = admin_name
                updated = True
            if not user.is_staff:
                user.is_staff = True
                updated = True
            if not user.is_superuser:
                user.is_superuser = True
                updated = True
            if updated:
                user.save(update_fields=["name", "is_staff", "is_superuser"])
                self.stdout.write(self.style.SUCCESS(f"Reconciled admin user: {admin_email}"))
            else:
                self.stdout.write(f"Admin user already exists: {admin_email}")
            return

        user = User.objects.create_user(
            username=admin_email,
            name=admin_name,
            password=admin_password,
        )
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Created admin user: {admin_email}"))

    def _validate_production_admin_config(self, admin_email: str, admin_password: str) -> None:
        """Enforce strict admin bootstrap rules in production."""
        weak_emails = {"admin@example.com", "admin"}
        weak_passwords = {"change-me", "admin", "admin123", "password"}

        if not admin_email:
            raise CommandError("ADMIN_EMAIL is required in production.")
        try:
            validate_email(admin_email)
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise CommandError("ADMIN_EMAIL must be a valid email address in production.") from exc

        if admin_email.lower() in weak_emails:
            raise CommandError("Default ADMIN_EMAIL is not allowed in production.")

        if not admin_password:
            raise CommandError("ADMIN_PASSWORD is required in production.")
        if admin_password in weak_passwords or len(admin_password) < 12:
            raise CommandError(
                "ADMIN_PASSWORD must be non-default and at least 12 characters in production."
            )
        try:
            validate_password(admin_password)
        except Exception as exc:  # pragma: no cover - framework message passthrough
            raise CommandError(f"ADMIN_PASSWORD failed validation in production: {exc}") from exc
