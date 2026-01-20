"""Django app configuration for submissions."""

from django.apps import AppConfig


class SubmissionsConfig(AppConfig):
    """AppConfig for submission tracking and grading."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "submissions"
