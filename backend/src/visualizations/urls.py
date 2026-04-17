"""Visualization URL routes — /api/v1/visualizations/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("dashboard", views.viz_dashboard, name="viz-dashboard"),
    path("courses/<int:course_id>/summary", views.viz_course_summary, name="viz-course-summary"),
    path(
        "assignments/<int:assignment_id>/summary",
        views.viz_assignment_summary,
        name="viz-assignment-summary",
    ),
    path(
        "assignments/<int:assignment_id>/mood-meter",
        views.viz_mood_meter,
        name="viz-mood-meter",
    ),
]
