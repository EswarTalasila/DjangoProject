"""Admin registrations for accounts models."""

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html

from courses.models import Course

from .models import (
    OAuthAccount,
    PasswordResetCode,
    PasswordResetRequest,
    RegistrationCode,
    RegistrationCodeType,
    ResearcherProfile,
    Role,
    StudentProfile,
    SudoGrant,
    SudoPermission,
    TeacherProfile,
    User,
    UserRole,
)
from .services._registration import create_registration_codes

SUDO_CAPABILITY_NOTE = (
    "Teacher registration code issuance is baseline for researchers and is not delegated "
    "through sudo permissions."
)
PERMISSION_LABELS = {
    SudoPermission.CREATE_TEACHER.value: "Create teachers",
    SudoPermission.CREATE_STUDENT.value: "Create students",
    SudoPermission.ISSUE_RESEARCHER_REG_CODE.value: "Issue researcher reg codes",
    SudoPermission.ISSUE_STUDENT_REG_CODE.value: "Issue student reg codes",
    SudoPermission.EDIT_USER.value: "Edit users",
    SudoPermission.DELETE_USER.value: "Delete users",
    SudoPermission.ISSUE_STUDENT_RESET_CODE.value: "Issue student reset codes",
    SudoPermission.ISSUE_RESEARCHER_RESET_CODE.value: "Issue researcher reset codes",
    SudoPermission.VIEW_SUBMISSIONS.value: "View submissions",
    SudoPermission.VIEW_IDENTIFIABLE_VIZ.value: "View identifiable viz",
    SudoPermission.EXPORT_IDENTIFIABLE.value: "Export identifiable data",
}
PERMISSION_GROUPS = (
    (
        "Registration Permissions",
        (
            SudoPermission.ISSUE_RESEARCHER_REG_CODE.value,
            SudoPermission.ISSUE_STUDENT_REG_CODE.value,
        ),
    ),
    (
        "Password Reset Permissions",
        (
            SudoPermission.ISSUE_STUDENT_RESET_CODE.value,
            SudoPermission.ISSUE_RESEARCHER_RESET_CODE.value,
        ),
    ),
    (
        "User Management Permissions",
        (
            SudoPermission.CREATE_TEACHER.value,
            SudoPermission.CREATE_STUDENT.value,
            SudoPermission.EDIT_USER.value,
            SudoPermission.DELETE_USER.value,
        ),
    ),
    (
        "Data Access Permissions",
        (
            SudoPermission.VIEW_SUBMISSIONS.value,
            SudoPermission.VIEW_IDENTIFIABLE_VIZ.value,
            SudoPermission.EXPORT_IDENTIFIABLE.value,
        ),
    ),
)


def _perm_field_name(value):
    """Map a SudoPermission value to its admin form BooleanField name."""
    return f"perm_{value}"


def _rows(values: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    """Render two boolean fields per row for denser admin forms."""
    rows: list[tuple[str, ...]] = []
    for index in range(0, len(values), 2):
        rows.append(tuple(_perm_field_name(v) for v in values[index : index + 2]))
    return tuple(rows)


def _build_permission_fieldsets():
    """Build one Django admin fieldset per permission category."""
    fieldsets = []
    for group_name, permission_values in PERMISSION_GROUPS:
        fieldsets.append((group_name, {"fields": _rows(permission_values)}))
    fieldsets.append((
        "Delegation Powers",
        {
            "fields": ("perm_can_grant_sudo",),
            "description": SUDO_CAPABILITY_NOTE,
        },
    ))
    return tuple(fieldsets)


_PERMISSION_FIELDSETS = _build_permission_fieldsets()


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admin configuration for user accounts."""

    list_display = ("username", "email", "name", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff")
    ordering = ("username",)
    search_fields = ("username", "email", "name")

    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Profile", {"fields": ("name",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """Admin configuration for user roles."""

    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username", "user__name")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Admin configuration for student profiles."""

    list_display = ("user", "consent", "created_by", "created_at")
    search_fields = ("user__username", "user__name")
    list_filter = ("consent",)


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    """Admin configuration for teacher profiles."""

    list_display = ("user", "created_at")
    search_fields = ("user__username", "user__name")


@admin.register(ResearcherProfile)
class ResearcherProfileAdmin(admin.ModelAdmin):
    """Admin configuration for researcher profiles with direct sudo management links."""

    list_display = (
        "user",
        "sudo_status",
        "sudo_permission_summary",
        "sudo_granted_by",
        "sudo_granted_at",
        "manage_sudo",
        "created_at",
    )
    list_filter = (
        ("user__sudo_grant__id", admin.EmptyFieldListFilter),
        "user__sudo_grant__can_grant_sudo",
    )
    search_fields = ("user__username", "user__name")
    list_select_related = ("user", "user__sudo_grant", "user__sudo_grant__granted_by")
    readonly_fields = ("manage_sudo",)
    search_help_text = "Search by researcher username or display name."
    fieldsets = (
        (None, {"fields": ("user", "created_at", "manage_sudo")}),
    )

    @admin.display(description="Sudo Status")
    def sudo_status(self, obj):
        """Show whether this researcher currently has a sudo grant."""
        return "Granted" if hasattr(obj.user, "sudo_grant") else "Not Granted"

    @admin.display(description="Permissions")
    def sudo_permission_summary(self, obj):
        """Show compact permission summary for quick scanning."""
        grant = getattr(obj.user, "sudo_grant", None)
        if not grant or not grant.permissions:
            return "—"
        rendered = [PERMISSION_LABELS.get(permission, permission) for permission in grant.permissions]
        if grant.can_grant_sudo:
            rendered.append("Grant Sudo Delegation")
        if len(rendered) <= 2:
            return ", ".join(rendered)
        return f"{', '.join(rendered[:2])} (+{len(rendered) - 2} more)"

    @admin.display(description="Granted By")
    def sudo_granted_by(self, obj):
        """Show who issued the sudo grant."""
        grant = getattr(obj.user, "sudo_grant", None)
        return grant.granted_by if grant else "—"

    @admin.display(description="Granted At")
    def sudo_granted_at(self, obj):
        """Show when sudo was granted."""
        grant = getattr(obj.user, "sudo_grant", None)
        return grant.granted_at if grant else "—"

    @admin.display(description="Sudo")
    def manage_sudo(self, obj):
        """Render a direct link to create or edit this researcher's sudo grant."""
        grant = getattr(obj.user, "sudo_grant", None)
        if grant:
            url = reverse("admin:accounts_sudogrant_change", args=[grant.pk])
            return format_html('<a class="button" href="{}">Edit sudo permissions</a>', url)
        url = f'{reverse("admin:accounts_sudogrant_add")}?user={obj.user_id}'
        return format_html('<a class="button" href="{}">Create sudo grant</a>', url)


class SudoGrantAdminForm(forms.ModelForm):
    """Admin form with researcher-only target selection and per-category permission checkboxes."""

    # Declare permission BooleanFields at class level so modelform_factory sees them.
    perm_ISSUE_RESEARCHER_REG_CODE = forms.BooleanField(label=PERMISSION_LABELS[SudoPermission.ISSUE_RESEARCHER_REG_CODE.value], required=False)
    perm_ISSUE_STUDENT_REG_CODE = forms.BooleanField(label=PERMISSION_LABELS[SudoPermission.ISSUE_STUDENT_REG_CODE.value], required=False)
    perm_ISSUE_STUDENT_RESET_CODE = forms.BooleanField(label=PERMISSION_LABELS[SudoPermission.ISSUE_STUDENT_RESET_CODE.value], required=False)
    perm_ISSUE_RESEARCHER_RESET_CODE = forms.BooleanField(label=PERMISSION_LABELS[SudoPermission.ISSUE_RESEARCHER_RESET_CODE.value], required=False)
    perm_CREATE_TEACHER = forms.BooleanField(label=PERMISSION_LABELS[SudoPermission.CREATE_TEACHER.value], required=False)
    perm_CREATE_STUDENT = forms.BooleanField(label=PERMISSION_LABELS[SudoPermission.CREATE_STUDENT.value], required=False)
    perm_EDIT_USER = forms.BooleanField(label=PERMISSION_LABELS[SudoPermission.EDIT_USER.value], required=False)
    perm_DELETE_USER = forms.BooleanField(label=PERMISSION_LABELS[SudoPermission.DELETE_USER.value], required=False)
    perm_VIEW_SUBMISSIONS = forms.BooleanField(label=PERMISSION_LABELS[SudoPermission.VIEW_SUBMISSIONS.value], required=False)
    perm_VIEW_IDENTIFIABLE_VIZ = forms.BooleanField(label=PERMISSION_LABELS[SudoPermission.VIEW_IDENTIFIABLE_VIZ.value], required=False)
    perm_EXPORT_IDENTIFIABLE = forms.BooleanField(label=PERMISSION_LABELS[SudoPermission.EXPORT_IDENTIFIABLE.value], required=False)
    perm_can_grant_sudo = forms.BooleanField(label="Grant sudo delegation", required=False)

    class Meta:
        model = SudoGrant
        fields = ("user", "granted_by")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = (
            User.objects.filter(roles__role=Role.RESEARCHER).distinct().order_by("name", "username")
        )
        self.fields["granted_by"].queryset = (
            User.objects.filter(Q(is_staff=True) | Q(sudo_grant__can_grant_sudo=True))
            .distinct()
            .order_by("name", "username")
        )
        self.fields["user"].help_text = (
            "Target researcher. To change this selection, create a new grant and delete the old one."
        )
        self.fields["granted_by"].help_text = (
            "Admin or researcher with 'Grant Sudo Delegation'. Defaults to current admin."
        )

        current_perms = list(self.instance.permissions or []) if self.instance.pk else []
        for _group_name, permission_values in PERMISSION_GROUPS:
            for value in permission_values:
                self.fields[_perm_field_name(value)].initial = value in current_perms
        self.fields["perm_can_grant_sudo"].initial = (
            self.instance.can_grant_sudo if self.instance.pk else False
        )

        if self.instance.pk:
            self.fields["user"].disabled = True

    def clean_user(self):
        """Require sudo grants to target a researcher account."""
        user = self.cleaned_data["user"]
        if not user.roles.filter(role=Role.RESEARCHER).exists():
            raise forms.ValidationError(
                "Sudo grants can only be assigned to users with the RESEARCHER role."
            )
        return user

    def _post_clean(self):
        """Assemble permissions before model validation so SudoGrant.clean() sees correct data."""
        permissions = []
        for _group_name, permission_values in PERMISSION_GROUPS:
            for value in permission_values:
                if self.cleaned_data.get(_perm_field_name(value)):
                    permissions.append(value)
        self.instance.permissions = permissions
        self.instance.can_grant_sudo = self.cleaned_data.get("perm_can_grant_sudo", False)
        super()._post_clean()


@admin.register(SudoGrant)
class SudoGrantAdmin(admin.ModelAdmin):
    """Admin configuration for sudo grants."""

    form = SudoGrantAdminForm
    list_display = (
        "id",
        "user",
        "permission_count",
        "permission_summary",
        "granted_by",
        "can_grant_sudo",
        "granted_at",
    )
    list_filter = ("can_grant_sudo", "granted_at")
    search_fields = ("user__username", "user__name", "granted_by__username", "granted_by__name")
    autocomplete_fields = ("user", "granted_by")
    readonly_fields = ("granted_at", "researcher_profile_link")
    ordering = ("-granted_at",)
    search_help_text = "Search by target researcher or granter."
    fieldsets = (
        ("Target", {"fields": ("user", "researcher_profile_link")}),
        ("Granted By", {"fields": ("granted_by",)}),
        *_PERMISSION_FIELDSETS,
        ("Audit", {"fields": ("granted_at",)}),
    )

    def get_queryset(self, request):
        """Use related-object loading for list rendering performance."""
        return super().get_queryset(request).select_related("user", "granted_by")

    def get_changeform_initial_data(self, request):
        """Pre-fill granter to the acting admin user on new grants."""
        initial = super().get_changeform_initial_data(request)
        initial.setdefault("granted_by", request.user.pk)
        return initial

    def get_form(self, request, obj=None, **kwargs):
        """Honor pre-selected researcher when opening from researcher profile."""
        form = super().get_form(request, obj, **kwargs)
        requested_user_id = request.GET.get("user")
        if obj is None and requested_user_id and "user" in form.base_fields:
            try:
                form.base_fields["user"].initial = int(requested_user_id)
            except ValueError:
                pass
        return form

    def save_model(self, request, obj, form, change):
        """Default granted_by to the acting admin when creating from admin UI."""
        if not change and not obj.granted_by_id:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="# Permissions")
    def permission_count(self, obj):
        """Display granted permission count in changelist."""
        return len(obj.permissions or [])

    @admin.display(description="Permissions")
    def permission_summary(self, obj):
        """Show a compact, readable summary instead of raw JSON."""
        if not obj.permissions:
            return "None"
        rendered = [PERMISSION_LABELS.get(permission, permission) for permission in obj.permissions]
        if obj.can_grant_sudo:
            rendered.append("Grant Sudo Delegation")
        if len(rendered) <= 3:
            return ", ".join(rendered)
        return f"{', '.join(rendered[:3])} (+{len(rendered) - 3} more)"

    @admin.display(description="Researcher Profile")
    def researcher_profile_link(self, obj):
        """Link back to the linked researcher's profile in admin."""
        try:
            profile_pk = obj.user.researcher_profile.pk
        except ResearcherProfile.DoesNotExist:
            return "No profile"
        url = reverse("admin:accounts_researcherprofile_change", args=[profile_pk])
        return format_html('<a href="{}">Open researcher profile</a>', url)


@admin.register(OAuthAccount)
class OAuthAccountAdmin(admin.ModelAdmin):
    """Admin configuration for linked OAuth accounts."""

    list_display = ("provider", "email", "user", "created_at", "last_login_at")
    search_fields = ("email", "subject", "user__username")
    list_filter = ("provider", "email_verified")


class RegistrationCodeAddForm(forms.Form):
    """Simplified form for generating registration codes via Django admin."""

    code_type = forms.ChoiceField(
        choices=RegistrationCodeType.choices,
        label="Code type",
    )
    count = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=1,
        label="Number of codes",
    )
    uses_per_code = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=1,
        label="Uses per code",
    )
    expires_at = forms.SplitDateTimeField(
        label="Expires at",
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"},
            time_attrs={"type": "time"},
        ),
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=False,
        label="Course (required for student codes)",
    )


@admin.register(RegistrationCode)
class RegistrationCodeAdmin(admin.ModelAdmin):
    """Admin configuration for invite/registration codes."""

    list_display = (
        "code_prefix",
        "code_type",
        "course",
        "is_active",
        "times_used",
        "max_uses",
        "expires_at",
        "archived_at",
    )
    list_filter = ("code_type", "is_active", "archived_at")
    search_fields = ("code_prefix", "course__name", "created_by__username")

    def get_readonly_fields(self, request, obj=None):
        """Make all fields read-only on the change form."""
        if obj:
            return [f.name for f in self.model._meta.fields]
        return ()

    def has_change_permission(self, request, obj=None):
        """Allow viewing existing codes but not editing them."""
        if obj:
            return True
        return super().has_change_permission(request, obj)

    def add_view(self, request, form_url="", extra_context=None):
        """Override add view to use the simplified code generation form."""
        if request.method == "POST":
            form = RegistrationCodeAddForm(request.POST)
            if form.is_valid():
                try:
                    created = create_registration_codes(
                        creator=request.user,
                        code_type=form.cleaned_data["code_type"],
                        count=form.cleaned_data["count"],
                        uses_per_code=form.cleaned_data["uses_per_code"],
                        expires_at=form.cleaned_data["expires_at"],
                        course_id=(
                            form.cleaned_data["course"].id
                            if form.cleaned_data["course"]
                            else None
                        ),
                    )
                    codes = [record.plaintext_code for record in created]
                    messages.success(
                        request,
                        f"Generated {len(codes)} {form.cleaned_data['code_type']} "
                        f"code(s): {', '.join(codes)}",
                    )
                    return HttpResponseRedirect(
                        reverse("admin:accounts_registrationcode_changelist")
                    )
                except (PermissionError, ValueError) as exc:
                    form.add_error(None, str(exc))
        else:
            form = RegistrationCodeAddForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Generate Registration Codes",
            "form": form,
            "opts": self.model._meta,
            "has_view_permission": True,
            "save_as": False,
            "save_on_top": False,
        }
        if extra_context:
            context.update(extra_context)

        from django.template.response import TemplateResponse

        return TemplateResponse(
            request,
            "admin/accounts/registrationcode/add_form.html",
            context,
        )


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    """Admin configuration for password reset requests."""

    list_display = ("id", "user", "status", "requested_at", "expires_at", "reviewed_by")
    list_filter = ("status",)
    search_fields = ("identifier", "user__username")


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    """Admin configuration for one-time password reset codes."""

    list_display = ("id", "request", "expires_at", "used_at", "created_at")
    search_fields = ("request__identifier", "request__user__username")
