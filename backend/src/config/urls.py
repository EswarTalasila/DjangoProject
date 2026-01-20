"""
URL configuration for EE-Lab-Personal project.

Routes all API endpoints under /api/ prefix for frontend compatibility.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Versioned API routes
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/courses/", include("courses.urls")),
    path("api/v1/assessments/", include("assessments.urls")),
    path("api/v1/assignments/", include("assignments.urls")),
    path("api/v1/submissions/", include("submissions.urls")),
    path("api/v1/students/", include("courses.urls_students")),
    path("api/v1/teachers/", include("accounts.urls_teachers")),
    path("api/v1/visualization/", include("visualizations.urls")),
    path("api/v1/export/", include("exports.urls")),
]
