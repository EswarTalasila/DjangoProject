"""Django app configuration for courses."""

from django.apps import AppConfig


class CoursesConfig(AppConfig):
    """AppConfig for courses and enrollments."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "courses"
