"""Management command to purge expired snapshot files."""

from django.core.management.base import BaseCommand

from packages.services import cleanup_expired_snapshots


class Command(BaseCommand):
    """Delete expired snapshots and their files."""

    help = "Purge expired data snapshots and their storage files."

    def handle(self, *args, **options):
        """Run snapshot cleanup and print summary."""
        result = cleanup_expired_snapshots()
        self.stdout.write(
            self.style.SUCCESS(
                "Cleanup complete: "
                f"snapshots_expired={result['snapshotsExpired']}, "
                f"files_deleted={result['filesDeleted']}"
            )
        )
