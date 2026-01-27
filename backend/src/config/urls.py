"""
URL configuration for EE-Lab-Personal project.

Routes all API endpoints under /api/ prefix for frontend compatibility.

API Documentation endpoints (via drf-spectacular):
    /api/docs/   - Swagger UI (interactive API explorer)
    /api/redoc/  - ReDoc (alternative documentation viewer)
    /api/schema/ - Raw OpenAPI 3.0 schema (YAML)

Debug toolbar (development only):
    /__debug__/  - Django Debug Toolbar panel
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

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
    # OpenAPI schema and documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Debug toolbar URLs (development only)
if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
        *urlpatterns,
    ]
