"""Export URL routes - /api/export/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.export_stub, name="export-stub"),
]
