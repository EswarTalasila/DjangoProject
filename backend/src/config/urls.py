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
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from accounts import views as account_views

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    # Versioned API routes
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/registration/", include("accounts.urls_registration")),
    # Collection aliases without trailing slash to match API standard.
    path("api/v1/users", account_views.create_user),
    path("api/v1/users/", include("accounts.urls_users")),
    # Top-level resources (moved from nested paths)
    path("api/v1/enrollments", account_views.join_course_with_code),
    path("api/v1/sudo-grants/me", account_views.my_sudo_grant),
    path("api/v1/sudo-grants", account_views.sudo_grants_collection),
    path("api/v1/sudo-grants/<int:grant_id>", account_views.revoke_sudo),
    path("api/v1/codes", account_views.codes_collection),
    path("api/v1/codes/", include("accounts.urls_codes")),
    path("api/v1/courses/", include("courses.urls")),
    path("api/v1/assessments/", include("assessments.urls")),
    path("api/v1/rubrics/", include("rubrics.urls")),
    path("api/v1/assignments/", include("assignments.urls")),
    path("api/v1/submissions/", include("submissions.urls")),
    path("api/v1/students/", include("courses.urls_students")),
    path("api/v1/teachers/", include("accounts.urls_teachers")),
    path("api/v1/visualizations/", include("visualizations.urls")),
    path("api/v1/exports/", include("exports.urls")),
]

if settings.ENVIRONMENT != "production":  # ENV-UC-05, ENV-CN-07
    urlpatterns += [
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
