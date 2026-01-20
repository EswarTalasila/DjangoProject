"""
WSGI config for EE-Lab-Personal project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os

from django.core.wsgi import get_wsgi_application

from config.otel import configure_tracing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

configure_tracing()
application = get_wsgi_application()
