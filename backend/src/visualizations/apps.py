"""Django app configuration for visualizations."""

from django.apps import AppConfig


class VisualizationsConfig(AppConfig):
    """AppConfig for reporting and visualization endpoints."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "visualizations"
