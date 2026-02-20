"""
Management command to provision deterministic role accounts through the real registration pipeline.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import models as db_models
from django.utils import timezone

from accounts.models import RegistrationCodeType
from accounts.services import (
    create_registration_codes,
    redeem_non_student_local_invite,
    redeem_student_invite,
)
from config.env import env
from courses.services import create_course

User = get_user_model()

# Non-admin account usernames are system-managed from first/last name.
CREDENTIALS = {
    "researcher": {
        "first_name": "Robin",
        "last_name": "Carter",
        "email": "researcher@example.com",
        "password": "change-me",
    },
    "teacher": {
        "first_name": "Morgan",
        "last_name": "Blake",
        "email": "teacher@example.com",
        "password": "change-me",
    },
    "student": {
        "first_name": "Alex",
        "last_name": "Torres",
        "password": "change-me",
    },
}

COURSE_NAME = "Dev Seed Course"

VALID_ROLES = list(CREDENTIALS.keys())


class Command(BaseCommand):
    """Provision accounts through the full registration pipeline."""

    help = "Create deterministic role accounts via real code generation and redemption."

    def add_arguments(self, parser):
        parser.add_argument(
            "--role",
            choices=[*VALID_ROLES, "all"],
            required=True,
            help="Which role account to provision (or 'all').",
        )

    def handle(self, *args, **options):
        if env.is_production:
            raise CommandError("provision_account is blocked in production.")

        role = options["role"]
        if role == "all":
            for r in VALID_ROLES:
                self._provision(r)
        else:
            self._provision(role)

    def _provision(self, role):
        creds = CREDENTIALS[role]
        existing = self._find_existing(role, creds)
        if existing:
            self._print_account(role, existing, creds, tag="already provisioned")
            return

        if role == "researcher":
            user = self._provision_researcher(creds)
        elif role == "teacher":
            self._ensure_provisioned("researcher")
            user = self._provision_teacher(creds)
        elif role == "student":
            self._ensure_provisioned("teacher")
            user = self._provision_student(creds)

        self._print_account(role, user, creds, tag="provisioned", success=True)

    def _find_existing(self, role, creds):
        full_name = f"{creds['first_name']} {creds['last_name']}".strip()
        if role == "student":
            return User.objects.filter(name=full_name).first()
        return User.objects.filter(db_models.Q(email__iexact=creds["email"])).first()

    def _print_account(self, role, user, creds, *, tag, success=False):
        parts = user.name.split(None, 1)
        first = parts[0] if parts else ""
        last = parts[1] if len(parts) > 1 else ""
        lines = [
            f"  {role} ({tag}):",
            f"    username:   {user.username}",
            f"    password:   {creds['password']}",
            f"    first name: {first}",
            f"    last name:  {last}",
        ]
        if user.email:
            lines.append(f"    email:      {user.email}")
        output = "\n".join(lines)
        if success:
            self.stdout.write(self.style.SUCCESS(output))
        else:
            self.stdout.write(output)

    def _ensure_provisioned(self, role):
        """Ensure a dependency role exists, provisioning it if needed."""
        creds = CREDENTIALS[role]
        if not self._find_existing(role, creds):
            self._provision(role)

    def _get_admin(self):
        admin = User.objects.filter(is_staff=True).first()
        if not admin:
            raise CommandError("No admin user found. Run 'manage.py ensure_admin' first.")
        return admin

    def _get_user(self, role):
        creds = CREDENTIALS[role]
        full_name = f"{creds['first_name']} {creds['last_name']}".strip()
        if role == "student":
            user = User.objects.filter(name=full_name).first()
        else:
            user = User.objects.filter(db_models.Q(email__iexact=creds["email"])).first()
        if not user:
            raise CommandError(f"Expected {role} user not found.")
        return user

    def _generate_code(self, creator, code_type, course=None):
        codes = create_registration_codes(
            creator=creator,
            code_type=code_type,
            count=1,
            uses_per_code=1,
            expires_at=timezone.now() + timedelta(hours=1),
            course_id=course.id if course else None,
        )
        return codes[0].plaintext_code

    def _provision_researcher(self, creds):
        admin = self._get_admin()
        raw_code = self._generate_code(admin, RegistrationCodeType.RESEARCHER)
        return redeem_non_student_local_invite(
            {
                "code": raw_code,
                "firstName": creds["first_name"],
                "lastName": creds["last_name"],
                "email": creds["email"],
                "password": creds["password"],
            }
        )

    def _provision_teacher(self, creds):
        researcher = self._get_user("researcher")
        raw_code = self._generate_code(researcher, RegistrationCodeType.TEACHER)
        return redeem_non_student_local_invite(
            {
                "code": raw_code,
                "firstName": creds["first_name"],
                "lastName": creds["last_name"],
                "email": creds["email"],
                "password": creds["password"],
            }
        )

    def _provision_student(self, creds):
        teacher = self._get_user("teacher")
        course = self._ensure_course(teacher)
        raw_code = self._generate_code(teacher, RegistrationCodeType.STUDENT, course=course)
        user, _enrollment = redeem_student_invite(
            {
                "code": raw_code,
                "firstName": creds["first_name"],
                "lastName": creds["last_name"],
                "password": creds["password"],
            }
        )
        return user

    def _ensure_course(self, teacher):
        from courses.models import Course

        existing = Course.objects.filter(name=COURSE_NAME, teacher_profile__user=teacher).first()
        if existing:
            return existing
        return create_course(teacher, COURSE_NAME)
