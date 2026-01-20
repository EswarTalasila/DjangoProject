"""Django app configuration for assessments."""

from django.apps import AppConfig


class AssessmentsConfig(AppConfig):
    """AppConfig for the assessments domain."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "assessments"
