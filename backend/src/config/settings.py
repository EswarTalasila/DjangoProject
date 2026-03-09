"""
Django settings for EE-Lab-Personal project.

Environment-based configuration for development and production.
Configuration is loaded via pydantic-settings for type safety and validation.
"""

from datetime import timedelta
from pathlib import Path
import logging

import dj_database_url

from config.env import env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.django_secret_key

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.debug
ENVIRONMENT = env.environment

ALLOWED_HOSTS = env.allowed_hosts_list

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "core",
    "accounts",
    "courses",
    "assessments",
    "rubrics",
    "assignments",
    "submissions",
    "visualizations",
    "exports",
    "packages",
]

# Development-only apps (not loaded in production)
# - debug_toolbar: SQL query inspection, request/response debugging
# - django_extensions: shell_plus with auto-imports, show_urls, graph_models
if env.debug_toolbar_enabled:
    INSTALLED_APPS += [
        "debug_toolbar",
        "django_extensions",
    ]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Debug toolbar middleware (insert after SecurityMiddleware)
if env.debug_toolbar_enabled:
    MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Custom templates directory for overriding third-party templates (e.g., Swagger UI)
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    "default": dj_database_url.parse(env.database_url, conn_max_age=600),
}

# Custom user model
AUTH_USER_MODEL = "accounts.User"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = Path("/app/staticfiles") if env.is_production else BASE_DIR / "staticfiles"
try:
    STATIC_ROOT.mkdir(parents=True, exist_ok=True)
except PermissionError:
    logging.warning("Could not create STATIC_ROOT at %s — ensure it exists and is writable", STATIC_ROOT)
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if env.is_production
        else "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Media files (user uploads — FR-15 Image Upload)
MEDIA_ROOT = Path(env.media_root) if env.media_root else BASE_DIR / "media"
try:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
except PermissionError:
    logging.warning("Could not create MEDIA_ROOT at %s — ensure it exists and is writable", MEDIA_ROOT)

# Package build storage — profile-driven base directory.
# Testing uses /tmp so builds don't depend on bind-mounted MEDIA_ROOT permissions.
import os as _os
import tempfile as _tempfile

if ENVIRONMENT == "testing":
    _PKG_BASE = Path(_tempfile.gettempdir()) / "eel-package-builds" / _os.getenv("PYTEST_XDIST_WORKER", "main")
else:
    _PKG_BASE = MEDIA_ROOT
PACKAGE_ARTIFACT_DIR = _PKG_BASE / "package_artifacts"
PACKAGE_SNAPSHOT_DIR = _PKG_BASE / "snapshots"
SUBMISSION_IMAGE_DIR = MEDIA_ROOT / "submissions"

for directory in (PACKAGE_ARTIFACT_DIR, PACKAGE_SNAPSHOT_DIR, SUBMISSION_IMAGE_DIR):
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logging.warning("Could not create directory at %s — ensure it exists and is writable", directory)

# Image upload constants (FR-15)
IMG_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
IMG_MAX_FILE_SIZE_BYTES = 10_485_760  # 10 MB
IMG_MAX_IMAGES_PER_SUBMISSION = 10

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "submissions": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "visualizations": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# CORS settings
CORS_ALLOWED_ORIGINS = env.cors_origins_list

CORS_ALLOW_CREDENTIALS = True

# Debug toolbar settings
# For Docker, we need to include the Docker network gateway
INTERNAL_IPS = ["127.0.0.1", "localhost"]
if env.debug_toolbar_enabled:
    import socket

    # Add Docker host IP for debug toolbar to work in containers
    try:
        hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
        INTERNAL_IPS += [ip[: ip.rfind(".")] + ".1" for ip in ips]
    except socket.gaierror:
        pass

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.authentication.CookieJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_EXCEPTION_HANDLER": "core.exception_handler.custom_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "anon_auth": "30/minute",
        "anon_burst": "10/minute",
    },
}

# drf-spectacular settings (OpenAPI/Swagger documentation)
# Generates OpenAPI 3.0 schema automatically from DRF views and serializers
# Access documentation at:
#   - /api/docs/   (Swagger UI - interactive)
#   - /api/redoc/  (ReDoc - clean reading)
#   - /api/schema/ (Raw OpenAPI YAML)
SPECTACULAR_SETTINGS = {
    "TITLE": "EE Lab Data Dashboard API",
    "DESCRIPTION": "API for managing educational assessments, submissions, and visualization.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,  # Don't include schema endpoint in schema itself
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,  # Enable deep links in Swagger UI
        "persistAuthorization": True,  # Keep auth tokens between page refreshes
        # Dark-friendly syntax highlighting for code blocks
        # Available themes: agate, arta, monokai, nord, obsidian, tomorrow-night, idea
        "syntaxHighlight.theme": "obsidian",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=24),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Google OAuth settings
GOOGLE_CLIENT_ID = env.google_client_id
GOOGLE_CLIENT_SECRET = env.google_client_secret

# Security settings
SECURE_BROWSER_XSS_FILTER = env.is_production
SECURE_CONTENT_TYPE_NOSNIFF = env.is_production
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_SECURE = env.csrf_cookie_secure
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env.session_cookie_secure
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_SSL_REDIRECT = env.ssl_redirect_enabled
SECURE_HSTS_SECONDS = 31536000 if env.is_production else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.is_production
SECURE_HSTS_PRELOAD = env.is_production

# Prevent Django from trying to chmod files on Windows/Docker volumes
FILE_UPLOAD_PERMISSIONS = None
