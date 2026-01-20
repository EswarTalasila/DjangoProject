"""Visualization URL routes - /api/visualization/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.get_visualizations, name="visualizations-data"),
]
