"""Registration code URL routes - /api/v1/codes/*"""

from django.urls import path

from . import views

urlpatterns = [
    path("<int:code_id>", views.code_detail, name="codes-detail"),
]
