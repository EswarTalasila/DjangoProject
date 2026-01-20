"""Django app configuration for core."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """AppConfig for shared core utilities."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
