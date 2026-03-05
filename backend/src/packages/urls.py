"""FR-16 URL routing for package workspace endpoints."""

from django.urls import path

from . import views

urlpatterns = [
    # PKG-UC-01: List/create workspaces
    path("workspaces", views.workspace_list_create_view, name="pkg-workspace-list-create"),
    # PKG-UC-01/02: Get/update workspace
    path("workspaces/<int:workspace_id>", views.workspace_detail, name="pkg-workspace-detail"),
    # PKG-UC-02: Add node
    path("workspaces/<int:workspace_id>/nodes", views.add_node_view, name="pkg-node-add"),
    # PKG-UC-02: Update/delete node
    path("workspaces/<int:workspace_id>/nodes/<int:node_id>", views.node_detail, name="pkg-node-detail"),
    # PKG-UC-03: Validate
    path("workspaces/<int:workspace_id>/validate", views.validate_workspace_view, name="pkg-validate"),
    # PKG-UC-04: Build
    path("workspaces/<int:workspace_id>/build", views.build_workspace_view, name="pkg-build"),
    # PKG-UC-04: Job status
    path("jobs/<int:job_id>", views.job_detail, name="pkg-job-detail"),
    # PKG-UC-05: Download artifact
    path("artifacts/<int:artifact_id>/download", views.download_artifact, name="pkg-artifact-download"),
]
