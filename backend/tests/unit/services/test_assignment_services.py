"""Pure unit tests for assignment service queries and mutations (no database)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from assignments.models import AudienceType

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# Helper: neutralise @transaction.atomic which was applied at import time.
# Patch Atomic.__enter__ and __exit__ so the context manager becomes a no-op.
# ---------------------------------------------------------------------------

class _NoopAtomicMixin:
    """Mixin that patches transaction.Atomic so it never touches the database."""

    def setup_method(self):
        self._p_enter = patch(
            "django.db.transaction.Atomic.__enter__", return_value=None
        )
        self._p_exit = patch(
            "django.db.transaction.Atomic.__exit__", return_value=False
        )
        self._p_enter.start()
        self._p_exit.start()

    def teardown_method(self):
        self._p_exit.stop()
        self._p_enter.stop()


# ---------------------------------------------------------------------------
# assignment_to_dto
# ---------------------------------------------------------------------------


class TestAssignmentToDto:
    """Tests for assignment_to_dto conversion."""

    def test_converts_assignment_to_dto(self):
        """Converts Assignment to AssignmentDTO with all fields."""
        from assignments.services._queries import assignment_to_dto

        now = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
        assignment_template = SimpleNamespace(title="Test AssignmentTemplate")
        assignment = SimpleNamespace(
            id=1,
            title="My Assignment",
            assignment_template_id=10,
            assignment_template=assignment_template,
            audience_type=AudienceType.COURSE,
            course_id=20,
            teacher_id=None,
            open_at=now,
            due_at=None,
            status="ACTIVE",
        )

        dto = assignment_to_dto(assignment)

        assert dto.id == 1
        assert dto.title == "My Assignment"
        assert dto.assignmentTemplateId == 10
        assert dto.assignmentTemplateTitle == "Test AssignmentTemplate"
        assert dto.audienceType == AudienceType.COURSE
        assert dto.courseId == 20
        assert dto.targetTeacherId is None
        assert dto.openAt == now
        assert dto.dueAt is None
        assert dto.status == "ACTIVE"

    def test_teacher_type_assignment(self):
        """Converts TEACHER-type assignment with teacher_id set."""
        from assignments.services._queries import assignment_to_dto

        now = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
        assignment_template = SimpleNamespace(title="Teacher AssignmentTemplate")
        assignment = SimpleNamespace(
            id=2,
            title="Teacher Self-AssignmentTemplate",
            assignment_template_id=11,
            assignment_template=assignment_template,
            audience_type=AudienceType.TEACHER,
            course_id=None,
            teacher_id=42,
            open_at=now,
            due_at=now,
            status="ACTIVE",
        )

        dto = assignment_to_dto(assignment)

        assert dto.audienceType == AudienceType.TEACHER
        assert dto.courseId is None
        assert dto.targetTeacherId == 42


# ---------------------------------------------------------------------------
# get_assignment
# ---------------------------------------------------------------------------


class TestGetAssignment:
    """Tests for get_assignment query."""

    @patch("assignments.services._queries.Assignment")
    def test_returns_assignment_when_found(self, mock_assignment_model):
        """Returns assignment when it exists."""
        from assignments.services._queries import get_assignment

        sentinel = SimpleNamespace(id=5)
        mock_assignment_model.objects.select_related.return_value.filter.return_value.first.return_value = sentinel

        result = get_assignment(5)

        assert result is sentinel

    @patch("assignments.services._queries.Assignment")
    def test_returns_none_when_not_found(self, mock_assignment_model):
        """Returns None when assignment does not exist."""
        from assignments.services._queries import get_assignment

        mock_assignment_model.objects.select_related.return_value.filter.return_value.first.return_value = None

        assert get_assignment(999) is None


# ---------------------------------------------------------------------------
# list_by_course
# ---------------------------------------------------------------------------


class TestListByCourse:
    """Tests for list_by_course query."""

    @patch("assignments.services._queries.Assignment")
    def test_returns_assignments_for_course(self, mock_assignment_model):
        """Returns list of assignments for a specific course (ACTIVE only by default)."""
        from assignments.services._queries import list_by_course

        sentinel = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        mock_qs = MagicMock()
        mock_assignment_model.objects.select_related.return_value.filter.return_value = mock_qs
        mock_qs.filter.return_value = sentinel

        result = list_by_course(10)

        assert result == sentinel


# ---------------------------------------------------------------------------
# list_for_user
# ---------------------------------------------------------------------------


class TestListForUser:
    """Tests for list_for_user query."""

    @patch("assignments.services._queries.timezone")
    @patch("assignments.services._queries.Enrollment")
    @patch("assignments.services._queries.Assignment")
    @patch("assignments.services._queries.primary_role", return_value="STUDENT")
    def test_student_sees_enrolled_course_assignments(
        self, mock_role, mock_assignment_model, mock_enrollment_model, mock_tz
    ):
        """Student sees assignments from courses they are enrolled in."""
        from assignments.services._queries import list_for_user

        now = datetime(2025, 6, 1, tzinfo=UTC)
        mock_tz.now.return_value = now

        # Mock enrollment queryset with values_list chain
        mock_enrollment_model.objects.filter.return_value.values_list.return_value = [10, 20]

        sentinel = [SimpleNamespace(id=1)]
        mock_qs = MagicMock()
        mock_assignment_model.objects.select_related.return_value.filter.return_value = mock_qs
        mock_qs.filter.return_value.order_by.return_value = sentinel

        user = SimpleNamespace(id=1, is_authenticated=True)

        result = list_for_user(user)

        assert result == sentinel

    @patch("assignments.services._queries.timezone")
    @patch("assignments.services._queries.Assignment")
    @patch("assignments.services._queries.primary_role", return_value="TEACHER")
    def test_teacher_sees_own_created_assignments(
        self, mock_role, mock_assignment_model, mock_tz
    ):
        """Teacher sees assignments they created."""
        from assignments.services._queries import list_for_user

        now = datetime(2025, 6, 1, tzinfo=UTC)
        mock_tz.now.return_value = now

        sentinel = [SimpleNamespace(id=2)]
        mock_qs = MagicMock()
        mock_assignment_model.objects.select_related.return_value.filter.return_value = mock_qs
        mock_qs.order_by.return_value = sentinel

        user = SimpleNamespace(id=42, is_authenticated=True)

        result = list_for_user(user)

        assert result == sentinel

    @patch("assignments.services._queries.primary_role", return_value="ADMIN")
    def test_non_student_non_teacher_returns_empty(self, mock_role):
        """Unknown role returns empty list."""
        from assignments.services._queries import list_for_user

        user = SimpleNamespace(id=1, is_authenticated=True)

        result = list_for_user(user)

        assert result == []


# ---------------------------------------------------------------------------
# create_assignment (mutation)
# ---------------------------------------------------------------------------


class TestCreateAssignment(_NoopAtomicMixin):
    """Tests for create_assignment mutation."""

    def test_raises_when_no_title(self):
        """Raises ValueError when title is missing or blank."""
        from assignments.services._mutations import create_assignment

        with pytest.raises(ValueError, match="title is required"):
            create_assignment(
                SimpleNamespace(id=1),
                {
                    "assignmentTemplateId": 1,
                    "audienceType": "COURSE",
                    "openAt": "now",
                },
            )

    def test_raises_when_no_assignment_template_id(self):
        """Raises ValueError when assignmentTemplateId is missing."""
        from assignments.services._mutations import create_assignment

        with pytest.raises(ValueError, match="assignmentTemplateId is required"):
            create_assignment(
                SimpleNamespace(id=1),
                {"title": "Week 1", "audienceType": "COURSE", "openAt": "now"},
            )

    def test_raises_when_no_audience_type(self):
        """Raises ValueError when audienceType is missing."""
        from assignments.services._mutations import create_assignment

        with pytest.raises(ValueError, match="audienceType is required"):
            create_assignment(
                SimpleNamespace(id=1),
                {"title": "Week 1", "assignmentTemplateId": 1, "openAt": "now"},
            )

    def test_raises_when_no_open_at(self):
        """Raises ValueError when openAt is missing."""
        from assignments.services._mutations import create_assignment

        with pytest.raises(ValueError, match="openAt is required"):
            create_assignment(
                SimpleNamespace(id=1),
                {"title": "Week 1", "assignmentTemplateId": 1, "audienceType": "COURSE"},
            )

    def test_raises_when_course_type_missing_course_id(self):
        """Raises ValueError when COURSE type has no courseId."""
        from assignments.services._mutations import create_assignment

        with pytest.raises(ValueError, match="courseId must be set"):
            create_assignment(
                SimpleNamespace(id=1),
                {
                    "title": "Week 1",
                    "assignmentTemplateId": 1,
                    "audienceType": AudienceType.COURSE,
                    "openAt": "2025-01-01",
                },
            )

    def test_raises_when_teacher_type_deprecated(self):
        """Raises ValueError when TEACHER audience type is used (deprecated)."""
        from assignments.services._mutations import create_assignment

        with pytest.raises(ValueError, match="TEACHER audience type is deprecated"):
            create_assignment(
                SimpleNamespace(id=1),
                {
                    "title": "Week 1",
                    "assignmentTemplateId": 1,
                    "audienceType": AudienceType.TEACHER,
                    "openAt": "2025-01-01",
                },
            )

    @patch("assignments.services._mutations.snapshot_assignment_content")
    @patch("assignments.services._mutations._create_submissions_for_course")
    @patch("assignments.services._mutations.Assignment")
    @patch("assignments.services._mutations.can_manage_course", return_value=True)
    @patch("assignments.services._mutations.Course")
    @patch("assignments.services._mutations.AssignmentTemplate")
    def test_creates_course_assignment_with_submissions(
        self, mock_assignment_template_model, mock_course_model, mock_can_manage,
        mock_assignment_model, mock_create_subs, mock_snapshot
    ):
        """Creates COURSE assignment and triggers submission creation."""
        from assignments.services._mutations import create_assignment
        from assignment_templates.models import AssignmentTemplateStatus

        fake_assignment_template = MagicMock()
        fake_assignment_template.id = 5
        fake_assignment_template.title = "Test"
        fake_assignment_template.status = AssignmentTemplateStatus.ACTIVE
        fake_assignment_template.has_been_used = False
        fake_assignment_template.used_at = None
        mock_assignment_template_model.objects.filter.return_value.first.return_value = (
            fake_assignment_template
        )
        fake_course = SimpleNamespace(id=10, status="ACTIVE")
        mock_course_model.objects.filter.return_value.first.return_value = fake_course

        fake_assignment = SimpleNamespace(id=1, course_id=10)
        mock_assignment_model.objects.create.return_value = fake_assignment

        user = SimpleNamespace(id=1)
        payload = {
            "title": "Week 1 Intro Check-in",
            "assignmentTemplateId": 5,
            "audienceType": AudienceType.COURSE,
            "courseId": 10,
            "openAt": "2025-01-01",
            "dueAt": None,
        }

        result = create_assignment(user, payload)

        assert result is fake_assignment
        mock_assignment_model.objects.create.assert_called_once_with(
            created_by=user,
            assignment_template_id=5,
            title="Week 1 Intro Check-in",
            audience_type=AudienceType.COURSE,
            course_id=10,
            teacher_id=None,
            open_at="2025-01-01",
            due_at=None,
            status="ACTIVE",
        )
        mock_snapshot.assert_called_once_with(
            fake_assignment,
            fake_assignment_template,
            creator_user_id=user.id,
        )
        mock_create_subs.assert_called_once_with(fake_assignment)

    @patch("assignments.services._mutations.timezone")
    @patch("assignments.services._mutations.snapshot_assignment_content")
    @patch("assignments.services._mutations._create_submissions_for_course")
    @patch("assignments.services._mutations.Assignment")
    @patch("assignments.services._mutations.can_manage_course", return_value=True)
    @patch("assignments.services._mutations.Course")
    @patch("assignments.services._mutations.AssignmentTemplate")
    def test_marks_assignment_template_as_used_on_first_assignment(
        self,
        mock_assignment_template_model,
        mock_course_model,
        mock_can_manage,
        mock_assignment_model,
        mock_create_subs,
        mock_snapshot,
        mock_tz,
    ):
        """Creating the first assignment stamps durable usage metadata on the template."""
        from assignments.services._mutations import create_assignment
        from assignment_templates.models import AssignmentTemplateStatus

        now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
        mock_tz.now.return_value = now

        fake_assignment_template = MagicMock()
        fake_assignment_template.id = 5
        fake_assignment_template.title = "Test"
        fake_assignment_template.status = AssignmentTemplateStatus.ACTIVE
        fake_assignment_template.has_been_used = False
        fake_assignment_template.used_at = None
        mock_assignment_template_model.objects.filter.return_value.first.return_value = (
            fake_assignment_template
        )
        fake_course = SimpleNamespace(id=10, status="ACTIVE")
        mock_course_model.objects.filter.return_value.first.return_value = fake_course

        fake_assignment = SimpleNamespace(id=1, course_id=10)
        mock_assignment_model.objects.create.return_value = fake_assignment

        user = SimpleNamespace(id=1)
        payload = {
            "title": "Week 1 Intro Check-in",
            "assignmentTemplateId": 5,
            "audienceType": AudienceType.COURSE,
            "courseId": 10,
            "openAt": datetime(2026, 4, 16, 12, 0, tzinfo=UTC),
            "dueAt": None,
        }

        create_assignment(user, payload)

        assert fake_assignment_template.has_been_used is True
        assert fake_assignment_template.used_at == now
        fake_assignment_template.save.assert_called_once_with(
            update_fields=["has_been_used", "used_at"]
        )

    @patch("assignments.services._mutations._create_submissions_for_course")
    @patch("assignments.services._mutations.Assignment")
    @patch("assignments.services._mutations.can_manage_course", return_value=True)
    @patch("assignments.services._mutations.Course")
    @patch("assignments.services._mutations.AssignmentTemplate")
    def test_does_not_mark_assignment_template_used_when_assignment_create_fails(
        self,
        mock_assignment_template_model,
        mock_course_model,
        mock_can_manage,
        mock_assignment_model,
        mock_create_subs,
    ):
        """A failed assignment create must not stamp the template as historically used."""
        from assignments.services._mutations import create_assignment
        from assignment_templates.models import AssignmentTemplateStatus

        fake_assignment_template = MagicMock()
        fake_assignment_template.id = 5
        fake_assignment_template.title = "Test"
        fake_assignment_template.status = AssignmentTemplateStatus.ACTIVE
        fake_assignment_template.has_been_used = False
        fake_assignment_template.used_at = None
        mock_assignment_template_model.objects.filter.return_value.first.return_value = (
            fake_assignment_template
        )
        fake_course = SimpleNamespace(id=10, status="ACTIVE")
        mock_course_model.objects.filter.return_value.first.return_value = fake_course
        mock_assignment_model.objects.create.side_effect = RuntimeError("boom")

        user = SimpleNamespace(id=1)
        payload = {
            "title": "Week 1 Intro Check-in",
            "assignmentTemplateId": 5,
            "audienceType": AudienceType.COURSE,
            "courseId": 10,
            "openAt": "2025-01-01",
            "dueAt": None,
        }

        with pytest.raises(RuntimeError, match="boom"):
            create_assignment(user, payload)

        assert fake_assignment_template.has_been_used is False
        assert fake_assignment_template.used_at is None
        fake_assignment_template.save.assert_not_called()

    def test_raises_when_open_at_after_due_at(self):
        """Raises ValueError when openAt >= dueAt."""
        from assignments.services._mutations import create_assignment

        with pytest.raises(ValueError, match="openAt must be before dueAt"):
            create_assignment(
                SimpleNamespace(id=1),
                {
                    "title": "Week 1",
                    "assignmentTemplateId": 1,
                    "audienceType": AudienceType.COURSE,
                    "courseId": 10,
                    "openAt": datetime(2025, 6, 2, tzinfo=UTC),
                    "dueAt": datetime(2025, 6, 1, tzinfo=UTC),
                },
            )

    @patch("assignments.services._mutations.AssignmentTemplate")
    def test_raises_when_assignment_template_not_found(self, mock_assignment_template):
        """Raises ValueError when assignment_template doesn't exist."""
        from assignments.services._mutations import create_assignment

        mock_assignment_template.objects.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="AssignmentTemplate not found"):
            create_assignment(
                SimpleNamespace(id=1),
                {
                    "title": "Week 1",
                    "assignmentTemplateId": 999,
                    "audienceType": AudienceType.COURSE,
                    "courseId": 10,
                    "openAt": datetime(2025, 1, 1, tzinfo=UTC),
                },
            )

    @patch("assignments.services._mutations.AssignmentTemplate")
    def test_raises_when_assignment_template_archived(self, mock_assignment_template):
        """Raises ConflictError when assignment_template is archived."""
        from assignments.services._mutations import ConflictError, create_assignment
        from assignment_templates.models import AssignmentTemplateStatus

        mock_assignment_template.objects.filter.return_value.first.return_value = SimpleNamespace(
            id=1, status=AssignmentTemplateStatus.ARCHIVED
        )

        with pytest.raises(ConflictError, match="archived assignment template"):
            create_assignment(
                SimpleNamespace(id=1),
                {
                    "title": "Week 1",
                    "assignmentTemplateId": 1,
                    "audienceType": AudienceType.COURSE,
                    "courseId": 10,
                    "openAt": datetime(2025, 1, 1, tzinfo=UTC),
                },
            )

    @patch("assignments.services._mutations.can_manage_course", return_value=False)
    @patch("assignments.services._mutations.Course")
    @patch("assignments.services._mutations.AssignmentTemplate")
    def test_raises_when_not_course_owner(
        self,
        mock_assignment_template,
        mock_course,
        mock_manage,
    ):
        """Raises ForbiddenError when user doesn't own the course."""
        from assignments.services._mutations import ForbiddenError, create_assignment
        from assignment_templates.models import AssignmentTemplateStatus

        mock_assignment_template.objects.filter.return_value.first.return_value = SimpleNamespace(
            id=1, status=AssignmentTemplateStatus.ACTIVE
        )
        mock_course.objects.filter.return_value.first.return_value = SimpleNamespace(
            id=10, status="ACTIVE"
        )

        with pytest.raises(ForbiddenError, match="do not own"):
            create_assignment(
                SimpleNamespace(id=1),
                {
                    "title": "Week 1",
                    "assignmentTemplateId": 1,
                    "audienceType": AudienceType.COURSE,
                    "courseId": 10,
                    "openAt": datetime(2025, 1, 1, tzinfo=UTC),
                },
            )

    @patch("assignments.services._mutations.Course")
    @patch("assignments.services._mutations.AssignmentTemplate")
    def test_raises_when_course_not_found(self, mock_assignment_template, mock_course):
        """Raises ValueError when course doesn't exist."""
        from assignments.services._mutations import create_assignment
        from assignment_templates.models import AssignmentTemplateStatus

        mock_assignment_template.objects.filter.return_value.first.return_value = SimpleNamespace(
            id=1, status=AssignmentTemplateStatus.ACTIVE
        )
        mock_course.objects.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Course not found"):
            create_assignment(
                SimpleNamespace(id=1),
                {
                    "title": "Week 1",
                    "assignmentTemplateId": 1,
                    "audienceType": AudienceType.COURSE,
                    "courseId": 999,
                    "openAt": datetime(2025, 1, 1, tzinfo=UTC),
                },
            )


# ---------------------------------------------------------------------------
# _create_submissions_for_course (internal)
# ---------------------------------------------------------------------------


class TestCreateSubmissionsForCourse(_NoopAtomicMixin):
    """Tests for _create_submissions_for_course internal helper."""

    def test_skips_when_assignment_has_no_course_id(self):
        """Skips submission creation when assignment has no course."""
        from assignments.services._mutations import _create_submissions_for_course

        assignment = SimpleNamespace(course_id=None)

        # Should not raise
        _create_submissions_for_course(assignment)

    @patch("assignments.services._mutations.provision_submission_answers")
    @patch("assignments.services._mutations.Submission")
    @patch("assignments.services._mutations.Enrollment")
    def test_creates_submissions_for_enrolled_students(
        self,
        mock_enrollment_model,
        mock_submission_model,
        mock_provision,
    ):
        """Creates submissions and provisions placeholder answers for each student."""
        from assignments.services._mutations import _create_submissions_for_course

        mock_enrollment_model.objects.filter.return_value.values_list.return_value = [
            100, 200
        ]
        mock_submission_model.objects.filter.return_value.exists.return_value = False
        fake_submission = SimpleNamespace(id=1)
        mock_submission_model.objects.create.return_value = fake_submission

        assignment = SimpleNamespace(id=1, assignment_template_id=5, course_id=10)

        _create_submissions_for_course(assignment)

        # 2 students, each gets 1 submission
        assert mock_submission_model.objects.create.call_count == 2
        assert mock_provision.call_count == 2

    @patch("assignments.services._mutations.Submission")
    @patch("assignments.services._mutations.Enrollment")
    def test_skips_existing_submissions(
        self,
        mock_enrollment_model,
        mock_submission_model,
    ):
        """Skips submission creation when submission already exists for student."""
        from assignments.services._mutations import _create_submissions_for_course

        mock_enrollment_model.objects.filter.return_value.values_list.return_value = [100]
        mock_submission_model.objects.filter.return_value.exists.return_value = True

        assignment = SimpleNamespace(id=1, assignment_template_id=5, course_id=10)

        _create_submissions_for_course(assignment)

        mock_submission_model.objects.create.assert_not_called()


# ---------------------------------------------------------------------------
# update_assignment (mutation)
# ---------------------------------------------------------------------------


class TestUpdateAssignment:
    """Tests for update_assignment mutation."""

    def test_raises_when_not_creator(self):
        """Raises ForbiddenError when caller is not the creator."""
        from assignments.services._mutations import ForbiddenError, update_assignment

        assignment = MagicMock()
        assignment.created_by_id = 1

        with pytest.raises(ForbiddenError, match="Only the assignment creator"):
            update_assignment(assignment, SimpleNamespace(id=2), {"title": "New"})

    def test_raises_when_archived(self):
        """Raises ConflictError when assignment is archived."""
        from assignments.services._mutations import ConflictError, update_assignment
        from assignments.models import AssignmentStatus

        assignment = MagicMock()
        assignment.created_by_id = 1
        assignment.status = AssignmentStatus.ARCHIVED

        with pytest.raises(ConflictError, match="archived assignment"):
            update_assignment(assignment, SimpleNamespace(id=1), {"title": "New"})

    def test_raises_when_open_at_after_due_at(self):
        """Raises ValueError when scheduling is invalid."""
        from assignments.services._mutations import update_assignment

        assignment = MagicMock()
        assignment.created_by_id = 1
        assignment.status = "ACTIVE"
        assignment.open_at = datetime(2025, 6, 1, tzinfo=UTC)
        assignment.due_at = datetime(2025, 7, 1, tzinfo=UTC)

        with pytest.raises(ValueError, match="openAt must be before dueAt"):
            update_assignment(
                assignment,
                SimpleNamespace(id=1),
                {
                    "openAt": datetime(2025, 8, 1, tzinfo=UTC),
                    "dueAt": datetime(2025, 7, 1, tzinfo=UTC),
                },
            )

    def test_updates_title(self):
        """Updates assignment title."""
        from assignments.services._mutations import update_assignment

        assignment = MagicMock()
        assignment.created_by_id = 1
        assignment.status = "ACTIVE"
        assignment.open_at = datetime(2025, 1, 1, tzinfo=UTC)
        assignment.due_at = None

        result = update_assignment(
            assignment, SimpleNamespace(id=1), {"title": "New Title"}
        )

        assert result.title == "New Title"
        assignment.save.assert_called_once()

    def test_raises_on_empty_title(self):
        """Raises ValueError when title is empty."""
        from assignments.services._mutations import update_assignment

        assignment = MagicMock()
        assignment.created_by_id = 1
        assignment.status = "ACTIVE"
        assignment.open_at = datetime(2025, 1, 1, tzinfo=UTC)
        assignment.due_at = None

        with pytest.raises(ValueError, match="title cannot be empty"):
            update_assignment(
                assignment, SimpleNamespace(id=1), {"title": "   "}
            )

    def test_handles_explicit_null_due_at(self):
        """Handles explicit null for dueAt."""
        from assignments.services._mutations import update_assignment

        assignment = MagicMock()
        assignment.created_by_id = 1
        assignment.status = "ACTIVE"
        assignment.open_at = datetime(2025, 1, 1, tzinfo=UTC)
        assignment.due_at = datetime(2025, 7, 1, tzinfo=UTC)

        result = update_assignment(
            assignment, SimpleNamespace(id=1), {"dueAt": None}
        )

        assert result.due_at is None


# ---------------------------------------------------------------------------
# archive_assignment (mutation)
# ---------------------------------------------------------------------------


class TestArchiveAssignment(_NoopAtomicMixin):
    """Tests for archive_assignment mutation."""

    @patch("assignments.services._mutations.timezone")
    def test_archives_active_assignment(self, mock_tz):
        """Archives an active assignment and sets status to ARCHIVED."""
        from assignments.services._mutations import archive_assignment

        mock_tz.now.return_value = "2025-01-01"
        assignment = MagicMock()
        assignment.status = "ACTIVE"
        assignment.created_by_id = 1

        user = SimpleNamespace(id=1, is_staff=False)
        result = archive_assignment(user, assignment)

        assert result.status == "ARCHIVED"
        assignment.save.assert_called_once()

    def test_raises_when_not_creator_or_admin(self):
        """Raises PermissionError when non-creator non-admin tries to archive."""
        from assignments.services._mutations import archive_assignment

        assignment = MagicMock()
        assignment.created_by_id = 1

        user = SimpleNamespace(id=2, is_staff=False)
        with pytest.raises(PermissionError, match="Only the assignment creator"):
            archive_assignment(user, assignment)

    def test_raises_when_already_archived(self):
        """Raises ConflictError when assignment is already archived."""
        from assignments.services._mutations import ConflictError, archive_assignment
        from assignments.models import AssignmentStatus

        assignment = MagicMock()
        assignment.status = AssignmentStatus.ARCHIVED
        assignment.created_by_id = 1

        user = SimpleNamespace(id=1, is_staff=False)
        with pytest.raises(ConflictError, match="already archived"):
            archive_assignment(user, assignment)

    @patch("assignments.services._mutations.timezone")
    def test_admin_can_archive(self, mock_tz):
        """Allows admin to archive an assignment they did not create."""
        from assignments.services._mutations import archive_assignment

        mock_tz.now.return_value = "2025-01-01"
        assignment = MagicMock()
        assignment.status = "ACTIVE"
        assignment.created_by_id = 99

        user = SimpleNamespace(id=1, is_staff=True)
        result = archive_assignment(user, assignment)

        assert result.status == "ARCHIVED"


# ---------------------------------------------------------------------------
# restore_assignment (mutation)
# ---------------------------------------------------------------------------


class TestRestoreAssignment(_NoopAtomicMixin):
    """Tests for restore_assignment mutation."""

    def test_raises_when_not_creator_or_admin(self):
        """Raises PermissionError when non-creator non-admin tries to restore."""
        from assignments.services._mutations import restore_assignment
        from assignments.models import AssignmentStatus

        assignment = MagicMock()
        assignment.created_by_id = 1
        assignment.status = AssignmentStatus.ARCHIVED

        user = SimpleNamespace(id=2, is_staff=False)
        with pytest.raises(PermissionError):
            restore_assignment(user, assignment)

    def test_raises_when_not_archived(self):
        """Raises ConflictError when restoring an assignment that is not archived."""
        from assignments.services._mutations import ConflictError, restore_assignment

        assignment = MagicMock()
        assignment.created_by_id = 1
        assignment.status = "ACTIVE"

        user = SimpleNamespace(id=1, is_staff=False)
        with pytest.raises(ConflictError, match="not archived"):
            restore_assignment(user, assignment)

    @patch("assignments.services._mutations.timezone")
    def test_restores_archived_assignment(self, mock_tz):
        """Restores an archived assignment back to ACTIVE status."""
        from assignments.services._mutations import restore_assignment
        from assignments.models import AssignmentStatus
        from assignment_templates.models import AssignmentTemplateStatus

        mock_tz.now.return_value = "2025-06-01"

        assignment = MagicMock()
        assignment.created_by_id = 1
        assignment.status = AssignmentStatus.ARCHIVED
        assignment.course_id = None
        assignment.assignment_template.status = AssignmentTemplateStatus.ACTIVE

        user = SimpleNamespace(id=1, is_staff=False)
        result = restore_assignment(user, assignment)

        assert result.status == "ACTIVE"
        assert result.archived_at is None

    @patch("assignments.services._mutations.timezone")
    def test_raises_when_course_archived(self, mock_tz):
        """Raises ConflictError when restoring an assignment whose course is archived."""
        from assignments.services._mutations import ConflictError, restore_assignment
        from assignments.models import AssignmentStatus

        assignment = MagicMock()
        assignment.created_by_id = 1
        assignment.status = AssignmentStatus.ARCHIVED
        assignment.course_id = 10
        assignment.course.status = "ARCHIVED"

        user = SimpleNamespace(id=1, is_staff=False)
        with pytest.raises(ConflictError, match="course is archived"):
            restore_assignment(user, assignment)

    @patch("assignments.services._mutations.timezone")
    def test_raises_when_assessment_archived(self, mock_tz):
        """Raises ConflictError when restoring an assignment whose assignment_template is archived."""
        from assignments.services._mutations import ConflictError, restore_assignment
        from assignments.models import AssignmentStatus
        from assignment_templates.models import AssignmentTemplateStatus

        assignment = MagicMock()
        assignment.created_by_id = 1
        assignment.status = AssignmentStatus.ARCHIVED
        assignment.course_id = None
        assignment.assignment_template.status = AssignmentTemplateStatus.ARCHIVED

        user = SimpleNamespace(id=1, is_staff=False)
        with pytest.raises(ConflictError, match="source assignment template is archived"):
            restore_assignment(user, assignment)


# ---------------------------------------------------------------------------
# purge_assignment (mutation)
# ---------------------------------------------------------------------------


class TestPurgeAssignment(_NoopAtomicMixin):
    """Tests for purge_assignment mutation."""

    def test_raises_when_not_archived(self):
        """Raises ConflictError when purging an assignment that is not archived."""
        from assignments.services._mutations import ConflictError, purge_assignment

        assignment = MagicMock()
        assignment.status = "ACTIVE"

        with pytest.raises(ConflictError, match="Only archived"):
            purge_assignment(assignment)

    @patch("assignments.services._mutations.Submission")
    def test_raises_when_progressed_submissions(self, mock_sub):
        """Raises ConflictError when assignment has progressed submissions."""
        from assignments.services._mutations import ConflictError, purge_assignment
        from assignments.models import AssignmentStatus

        assignment = MagicMock()
        assignment.status = AssignmentStatus.ARCHIVED
        mock_sub.objects.filter.return_value.exclude.return_value.exists.return_value = True

        with pytest.raises(ConflictError, match="progressed"):
            purge_assignment(assignment)

    @patch("assignments.services._archive_exports.cleanup_assignment_archive_artifacts")
    @patch("submissions.image_services.cleanup_images_for_submission")
    @patch("assignments.services._mutations.Submission")
    def test_purges_successfully(
        self,
        mock_sub,
        mock_cleanup_images,
        mock_cleanup_artifacts,
    ):
        """Permanently deletes an archived assignment and cleans up submission images."""
        from assignments.services._mutations import purge_assignment
        from assignments.models import AssignmentStatus

        assignment = MagicMock()
        assignment.status = AssignmentStatus.ARCHIVED
        mock_sub.objects.filter.return_value.exclude.return_value.exists.return_value = False

        sub1 = MagicMock(id=1)
        sub2 = MagicMock(id=2)
        assignment.submissions.all.return_value = [sub1, sub2]

        purge_assignment(assignment)

        assert mock_cleanup_images.call_count == 2
        mock_cleanup_artifacts.assert_called_once_with(assignment)
        assignment.delete.assert_called_once()
