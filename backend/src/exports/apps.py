"""Django app configuration for exports."""

from django.apps import AppConfig


class ExportsConfig(AppConfig):
    """AppConfig for export endpoints."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "exports"
