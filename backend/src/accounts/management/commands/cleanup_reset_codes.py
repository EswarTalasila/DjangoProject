"""Management command to purge temporary password reset code records."""

from django.core.management.base import BaseCommand

from accounts.services import cleanup_temporary_reset_codes


class Command(BaseCommand):
    """Delete expired/used password reset codes per AUTH-CN-09."""

    help = "Purge expired and used password reset codes."

    def handle(self, *args, **options):
        """Run reset-code cleanup and print deletion summary."""
        result = cleanup_temporary_reset_codes()
        self.stdout.write(
            self.style.SUCCESS(
                "Cleanup complete: "
                f"codes_deleted={result['codesDeleted']}, "
                f"requests_expired={result['requestsExpired']}"
            )
        )
