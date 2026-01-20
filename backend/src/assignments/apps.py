"""Django app configuration for assignments."""

from django.apps import AppConfig


class AssignmentsConfig(AppConfig):
    """AppConfig for assignment scheduling."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "assignments"
