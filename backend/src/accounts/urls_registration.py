"""Registration URL routes - /api/v1/registration/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("validate-code", views.validate_registration_code_view, name="registration-validate-code"),
    path("local", views.register_local, name="registration-local"),
    path("oauth", views.register_oauth, name="registration-oauth"),
    path("student/join-course", views.join_course_with_code, name="registration-student-join"),
]
