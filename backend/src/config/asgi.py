"""
ASGI config for EE-Lab-Personal project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os

from django.core.asgi import get_asgi_application

from config.otel import configure_tracing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

configure_tracing()
application = get_asgi_application()
