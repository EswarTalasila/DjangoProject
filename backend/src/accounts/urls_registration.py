"""Registration URL routes - /api/v1/registration/*"""

from django.urls import path

from . import views

urlpatterns = [
    path(
        "code-validations",
        views.validate_registration_code_view,
        name="registration-code-validations",
    ),
    path("accounts", views.register_account, name="registration-accounts"),
]
