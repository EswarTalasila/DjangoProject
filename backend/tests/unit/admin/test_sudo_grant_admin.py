"""Unit tests for Django admin usability around SudoGrant management."""

from __future__ import annotations

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from accounts.admin import (
    ResearcherProfileAdmin,
    SudoGrantAdmin,
    SudoGrantAdminForm,
    _perm_field_name,
)
from accounts.models import ResearcherProfile, Role, SudoGrant, SudoPermission, User, UserRole


@pytest.mark.django_db
@pytest.mark.unit
def test_sudo_grant_form_targets_researchers_only(admin_user, researcher_user, teacher_user):
    """SudoGrant form only offers researcher accounts in the target dropdown."""

    form = SudoGrantAdminForm()
    researcher_targets = list(form.fields["user"].queryset.values_list("id", flat=True))

    assert researcher_user.id in researcher_targets
    assert teacher_user.id not in researcher_targets
    assert admin_user.id not in researcher_targets


@pytest.mark.django_db
@pytest.mark.unit
def test_sudo_grant_form_rejects_non_researcher_target(admin_user, teacher_user):
    """Non-researcher target user ids are rejected by the admin form."""

    data = {
        "user": teacher_user.id,
        "granted_by": admin_user.id,
    }
    form = SudoGrantAdminForm(data=data)

    assert not form.is_valid()
    assert "user" in form.errors


@pytest.mark.django_db
@pytest.mark.unit
def test_sudo_grant_form_boolean_fields_collect_into_permissions(admin_user, researcher_user):
    """Per-category boolean fields are collected into the permissions JSON list on save."""

    data = {
        "user": researcher_user.id,
        "granted_by": admin_user.id,
        _perm_field_name(SudoPermission.CREATE_STUDENT.value): True,
        _perm_field_name(SudoPermission.EDIT_USER.value): True,
        "perm_can_grant_sudo": True,
    }
    form = SudoGrantAdminForm(data=data)
    assert form.is_valid(), form.errors

    grant = form.save()

    assert SudoPermission.CREATE_STUDENT.value in grant.permissions
    assert SudoPermission.EDIT_USER.value in grant.permissions
    assert grant.can_grant_sudo is True
    assert len(grant.permissions) == 2


@pytest.mark.django_db
@pytest.mark.unit
def test_sudo_grant_form_initial_reflects_existing_permissions(admin_user, researcher_user):
    """Existing grants pre-populate individual boolean fields correctly."""

    grant = SudoGrant.objects.create(
        user=researcher_user,
        granted_by=admin_user,
        permissions=[SudoPermission.CREATE_STUDENT.value, SudoPermission.DELETE_USER.value],
        can_grant_sudo=True,
    )

    form = SudoGrantAdminForm(instance=grant)

    assert form.fields[_perm_field_name(SudoPermission.CREATE_STUDENT.value)].initial is True
    assert form.fields[_perm_field_name(SudoPermission.DELETE_USER.value)].initial is True
    assert form.fields[_perm_field_name(SudoPermission.EDIT_USER.value)].initial is False
    assert form.fields["perm_can_grant_sudo"].initial is True


@pytest.mark.django_db
@pytest.mark.unit
def test_sudo_grant_form_disables_target_on_existing_grant(admin_user, researcher_user):
    """Editing an existing grant locks target researcher selection."""

    grant = SudoGrant.objects.create(
        user=researcher_user,
        granted_by=admin_user,
        permissions=[SudoPermission.CREATE_STUDENT.value],
        can_grant_sudo=False,
    )
    form = SudoGrantAdminForm(instance=grant)

    assert form.fields["user"].disabled is True


@pytest.mark.django_db
@pytest.mark.unit
def test_sudo_grant_admin_prefills_granted_by_from_request_user(admin_user):
    """Admin helper pre-fills granted_by to the acting admin on add form."""

    model_admin = SudoGrantAdmin(SudoGrant, AdminSite())
    request = RequestFactory().get("/admin/accounts/sudogrant/add/")
    request.user = admin_user

    initial = model_admin.get_changeform_initial_data(request)

    assert initial["granted_by"] == admin_user.pk


@pytest.mark.django_db
@pytest.mark.unit
def test_sudo_grant_admin_save_defaults_granted_by(admin_user):
    """Creating a grant without explicit granter defaults to request.user."""

    researcher = User.objects.create_user(
        username="sudo-target",
        email="sudo-target@example.com",
        name="Sudo Target",
        password="StartPass123!",
    )
    UserRole.objects.create(user=researcher, role=Role.RESEARCHER)

    model_admin = SudoGrantAdmin(SudoGrant, AdminSite())
    request = RequestFactory().post("/admin/accounts/sudogrant/add/")
    request.user = admin_user

    grant = SudoGrant(
        user=researcher,
        permissions=[SudoPermission.CREATE_STUDENT],
        can_grant_sudo=False,
    )
    model_admin.save_model(request, grant, form=None, change=False)

    saved = SudoGrant.objects.get(pk=grant.pk)
    assert saved.granted_by_id == admin_user.id


@pytest.mark.django_db
@pytest.mark.unit
def test_researcher_profile_admin_manage_sudo_link_targets_add(admin_user, researcher_user):
    """Researcher profile shows create link when sudo grant is missing."""

    model_admin = ResearcherProfileAdmin(ResearcherProfile, AdminSite())
    profile = researcher_user.researcher_profile
    rendered = model_admin.manage_sudo(profile)

    assert "Create sudo grant" in rendered
    assert f"user={researcher_user.id}" in rendered


@pytest.mark.django_db
@pytest.mark.unit
def test_researcher_profile_admin_manage_sudo_link_targets_change(admin_user, researcher_user):
    """Researcher profile shows edit link when sudo grant exists."""

    grant = SudoGrant.objects.create(
        user=researcher_user,
        granted_by=admin_user,
        permissions=[SudoPermission.CREATE_STUDENT.value],
        can_grant_sudo=False,
    )
    model_admin = ResearcherProfileAdmin(ResearcherProfile, AdminSite())
    profile = researcher_user.researcher_profile
    rendered = model_admin.manage_sudo(profile)

    assert "Edit sudo permissions" in rendered
    assert f"/accounts/sudogrant/{grant.id}/change/" in rendered


@pytest.mark.django_db
@pytest.mark.unit
def test_sudo_grant_fieldsets_include_permission_categories():
    """SudoGrantAdmin fieldsets contain separate sections for each permission category."""

    model_admin = SudoGrantAdmin(SudoGrant, AdminSite())
    fieldset_names = [name for name, _opts in model_admin.fieldsets]

    assert "Registration Permissions" in fieldset_names
    assert "Password Reset Permissions" in fieldset_names
    assert "User Management Permissions" in fieldset_names
    assert "Data Access Permissions" in fieldset_names
    assert "Delegation Powers" in fieldset_names
