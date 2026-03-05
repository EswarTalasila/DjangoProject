"""Django app configuration for packages."""

from django.apps import AppConfig


class PackagesConfig(AppConfig):
    """AppConfig for the packaging workspace domain (FR-16)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "packages"
