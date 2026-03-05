from django.urls import path

from . import views

urlpatterns = [
    path("courses/<int:course_id>/roster", views.course_roster, name="export-roster"),
    path("courses/<int:course_id>/submissions", views.course_submissions, name="export-course-submissions"),
]
