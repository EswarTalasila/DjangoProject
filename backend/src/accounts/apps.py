"""Django app configuration for accounts."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """AppConfig for user accounts and authentication."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
