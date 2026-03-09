"""Pure unit tests for course service queries and mutations (no database)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from accounts.models import Role
from courses.models import EnrollmentStatus

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# Helper: neutralise @transaction.atomic which was applied at import time.
# We cannot swap the module-level `transaction` object because the function
# has already been decorated. Instead we patch the Atomic context-manager
# protocol so __enter__/__exit__ become no-ops.
# Mutation test classes inherit from this mixin.
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
# _teacher_profile_for
# ---------------------------------------------------------------------------


class TestTeacherProfileFor:
    """Tests for _teacher_profile_for helper."""

    @patch("courses.services._queries.TeacherProfile")
    def test_returns_profile_when_exists(self, mock_tp_model):
        """Returns TeacherProfile when user has one."""
        from courses.services._queries import _teacher_profile_for

        fake_profile = SimpleNamespace(id=1)
        mock_tp_model.objects.filter.return_value.first.return_value = fake_profile
        user = SimpleNamespace(id=10)

        result = _teacher_profile_for(user)

        assert result is fake_profile
        mock_tp_model.objects.filter.assert_called_once_with(user=user)

    @patch("courses.services._queries.TeacherProfile")
    def test_returns_none_when_no_profile(self, mock_tp_model):
        """Returns None when user has no TeacherProfile."""
        from courses.services._queries import _teacher_profile_for

        mock_tp_model.objects.filter.return_value.first.return_value = None
        user = SimpleNamespace(id=10)

        result = _teacher_profile_for(user)

        assert result is None


# ---------------------------------------------------------------------------
# _course_owner
# ---------------------------------------------------------------------------


class TestCourseOwner:
    """Tests for _course_owner helper."""

    def test_returns_none_when_no_teacher_profile(self):
        """Returns None when course has no teacher_profile."""
        from courses.services._queries import _course_owner

        course = SimpleNamespace(teacher_profile=None)
        assert _course_owner(course) is None

    def test_returns_user_from_teacher_profile(self):
        """Returns the user object from teacher_profile."""
        from courses.services._queries import _course_owner

        user = SimpleNamespace(id=5, name="Teacher")
        course = SimpleNamespace(teacher_profile=SimpleNamespace(user=user))

        assert _course_owner(course) is user


# ---------------------------------------------------------------------------
# can_view_course
# ---------------------------------------------------------------------------


class TestCanViewCourse:
    """Tests for can_view_course permission check."""

    def test_admin_can_view_any_course(self):
        """Admin (is_staff) can view any course."""
        from courses.services._queries import can_view_course

        admin = SimpleNamespace(id=1, is_staff=True)
        course = SimpleNamespace(teacher_profile=None)

        assert can_view_course(admin, course) is True

    @patch("courses.services._queries.has_role", return_value=True)
    def test_researcher_can_view_any_course(self, mock_has_role):
        """Researcher role grants view access to any course."""
        from courses.services._queries import can_view_course

        researcher = SimpleNamespace(id=2, is_staff=False)
        course = SimpleNamespace(teacher_profile=None)

        assert can_view_course(researcher, course) is True
        mock_has_role.assert_called_once_with(researcher, Role.RESEARCHER)

    @patch("courses.services._queries.has_role", return_value=False)
    def test_teacher_can_view_own_course(self, mock_has_role):
        """Teacher can view their own course."""
        from courses.services._queries import can_view_course

        user = SimpleNamespace(id=10, is_staff=False)
        course = SimpleNamespace(
            teacher_profile=SimpleNamespace(user=SimpleNamespace(id=10))
        )

        assert can_view_course(user, course) is True

    @patch("courses.services._queries.has_role", return_value=False)
    def test_teacher_cannot_view_other_course(self, mock_has_role):
        """Teacher cannot view another teacher's course."""
        from courses.services._queries import can_view_course

        user = SimpleNamespace(id=10, is_staff=False)
        course = SimpleNamespace(
            teacher_profile=SimpleNamespace(user=SimpleNamespace(id=99))
        )

        assert can_view_course(user, course) is False

    @patch("courses.services._queries.has_role", return_value=False)
    def test_returns_false_when_no_owner(self, mock_has_role):
        """Returns False for non-admin user when course has no owner."""
        from courses.services._queries import can_view_course

        user = SimpleNamespace(id=10, is_staff=False)
        course = SimpleNamespace(teacher_profile=None)

        assert can_view_course(user, course) is False


# ---------------------------------------------------------------------------
# can_manage_course
# ---------------------------------------------------------------------------


class TestCanManageCourse:
    """Tests for can_manage_course permission check."""

    def test_owner_can_manage(self):
        """Course owner can manage (edit/delete)."""
        from courses.services._queries import can_manage_course

        user = SimpleNamespace(id=7, is_staff=False)
        course = SimpleNamespace(
            teacher_profile=SimpleNamespace(user=SimpleNamespace(id=7))
        )

        assert can_manage_course(user, course) is True

    def test_non_owner_cannot_manage(self):
        """Non-owner user cannot manage course."""
        from courses.services._queries import can_manage_course

        user = SimpleNamespace(id=7, is_staff=False)
        course = SimpleNamespace(
            teacher_profile=SimpleNamespace(user=SimpleNamespace(id=99))
        )

        assert can_manage_course(user, course) is False

    def test_returns_false_when_no_teacher_profile(self):
        """Returns False when course has no teacher_profile (no owner)."""
        from courses.services._queries import can_manage_course

        user = SimpleNamespace(id=7)
        course = SimpleNamespace(teacher_profile=None)

        assert can_manage_course(user, course) is False


# ---------------------------------------------------------------------------
# enrollment_to_student_dto
# ---------------------------------------------------------------------------


class TestEnrollmentToStudentDto:
    """Tests for enrollment_to_student_dto conversion."""

    def test_converts_enrollment_with_user(self):
        """Converts enrollment to DTO with user info."""
        from courses.services._queries import enrollment_to_student_dto

        user = SimpleNamespace(id=42, name="Alice", username="alice123")
        student_profile = SimpleNamespace(user=user, consent=True)
        enrollment = SimpleNamespace(
            student_profile=student_profile, course_id=10, enrolled_at=None
        )

        dto = enrollment_to_student_dto(enrollment)

        assert dto.id == 42
        assert dto.name == "Alice"
        assert dto.username == "alice123"
        assert dto.role == "STUDENT"
        assert dto.consent is True
        assert dto.courseId == 10

    def test_handles_none_student_profile(self):
        """Handles enrollment with None student_profile gracefully."""
        from courses.services._queries import enrollment_to_student_dto

        enrollment = SimpleNamespace(
            student_profile=None, course_id=10, enrolled_at=None
        )

        dto = enrollment_to_student_dto(enrollment)

        assert dto.id is None
        assert dto.name is None
        assert dto.username is None
        assert dto.consent is False

    def test_consent_false_by_default(self):
        """Consent defaults to False when profile exists but consent is False."""
        from courses.services._queries import enrollment_to_student_dto

        user = SimpleNamespace(id=1, name="Bob", username="bob")
        student_profile = SimpleNamespace(user=user, consent=False)
        enrollment = SimpleNamespace(
            student_profile=student_profile, course_id=5, enrolled_at=None
        )

        dto = enrollment_to_student_dto(enrollment)

        assert dto.consent is False


# ---------------------------------------------------------------------------
# course_to_dto
# ---------------------------------------------------------------------------


class TestCourseToDto:
    """Tests for course_to_dto conversion."""

    @patch("courses.services._queries.Assignment")
    @patch("courses.services._queries.Enrollment")
    def test_converts_course_to_dto(self, mock_enrollment_model, mock_assignment_model):
        """Converts Course to CourseDTO with students and assignment IDs."""
        from courses.services._queries import course_to_dto

        teacher_user = SimpleNamespace(id=42, name="Teacher Smith")
        user = SimpleNamespace(id=1, name="Student1", username="s1")
        student_profile = SimpleNamespace(user=user, consent=True)
        enrollment = SimpleNamespace(
            student_profile=student_profile, course_id=100, enrolled_at=None
        )
        mock_enrollment_model.objects.filter.return_value = [enrollment]
        mock_assignment_model.objects.filter.return_value.values_list.return_value = [5, 6]

        course = SimpleNamespace(
            id=100, name="Math 101", teacher_profile_id=42,
            teacher_profile=SimpleNamespace(user=teacher_user),
            created_at=None,
        )

        dto = course_to_dto(course)

        assert dto.id == 100
        assert dto.name == "Math 101"
        assert dto.studentCount == 1
        assert dto.assignmentIds == [5, 6]
        assert dto.teacherId == 42
        assert dto.teacherName == "Teacher Smith"

    @patch("courses.services._queries.Assignment")
    @patch("courses.services._queries.Enrollment")
    def test_empty_course_produces_zero_counts(self, mock_enrollment_model, mock_assignment_model):
        """Course with no enrollments or assignments returns zero counts."""
        from courses.services._queries import course_to_dto

        mock_enrollment_model.objects.filter.return_value = []
        mock_assignment_model.objects.filter.return_value.values_list.return_value = []

        course = SimpleNamespace(
            id=1, name="Empty", teacher_profile_id=None,
            teacher_profile=None,
            created_at=None,
        )

        dto = course_to_dto(course)

        assert dto.studentCount == 0
        assert dto.students == []
        assert dto.assignmentIds == []
        assert dto.teacherId is None


# ---------------------------------------------------------------------------
# list_courses_for_user
# ---------------------------------------------------------------------------


class TestListCoursesForUser:
    """Tests for list_courses_for_user query."""

    @patch("courses.services._queries.Course")
    def test_admin_sees_all_courses(self, mock_course_model):
        """Admin (is_staff) sees all active courses by default."""
        from courses.services._queries import list_courses_for_user

        sentinel = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        mock_qs = MagicMock()
        mock_course_model.objects.all.return_value = mock_qs
        mock_qs.filter.return_value = sentinel

        admin = SimpleNamespace(id=1, is_staff=True, is_authenticated=True)

        result = list_courses_for_user(admin)

        assert result == sentinel

    @patch("courses.services._queries.has_role", return_value=True)
    @patch("courses.services._queries.Course")
    def test_researcher_sees_all_courses(self, mock_course_model, mock_has_role):
        """Researcher sees all active courses."""
        from courses.services._queries import list_courses_for_user

        sentinel = [SimpleNamespace(id=1)]
        mock_qs = MagicMock()
        mock_course_model.objects.all.return_value = mock_qs
        mock_qs.filter.return_value = sentinel

        researcher = SimpleNamespace(id=2, is_staff=False, is_authenticated=True)

        result = list_courses_for_user(researcher)

        assert result == sentinel

    @patch("courses.services._queries.has_role", return_value=False)
    @patch("courses.services._queries.Course")
    def test_teacher_sees_own_courses(self, mock_course_model, mock_has_role):
        """Teacher sees only their own active courses."""
        from courses.services._queries import list_courses_for_user

        sentinel = [SimpleNamespace(id=3)]
        mock_qs = MagicMock()
        mock_filtered_qs = MagicMock()
        mock_course_model.objects.all.return_value = mock_qs
        # First .filter(status=ACTIVE) returns a filtered queryset
        mock_qs.filter.return_value = mock_filtered_qs
        # Second .filter(teacher_profile__user=user) returns sentinel
        mock_filtered_qs.filter.return_value = sentinel

        teacher = SimpleNamespace(id=5, is_staff=False, is_authenticated=True)

        result = list_courses_for_user(teacher)

        assert result == sentinel


# ---------------------------------------------------------------------------
# list_students_in_course
# ---------------------------------------------------------------------------


class TestListStudentsInCourse:
    """Tests for list_students_in_course query."""

    @patch("courses.services._queries.Enrollment")
    def test_returns_student_dtos(self, mock_enrollment_model):
        """Returns list of EnrollmentStudentDTO objects."""
        from courses.services._queries import list_students_in_course

        user = SimpleNamespace(id=1, name="Student", username="s1")
        student_profile = SimpleNamespace(user=user, consent=True)
        enrollment = SimpleNamespace(
            student_profile=student_profile, course_id=10, enrolled_at=None
        )
        mock_enrollment_model.objects.filter.return_value = [enrollment]

        course = SimpleNamespace(id=10)

        result = list_students_in_course(course)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "Student"

    @patch("courses.services._queries.Enrollment")
    def test_empty_course_returns_empty_list(self, mock_enrollment_model):
        """Returns empty list when no enrollments exist."""
        from courses.services._queries import list_students_in_course

        mock_enrollment_model.objects.filter.return_value = []

        result = list_students_in_course(SimpleNamespace(id=10))

        assert result == []


# ---------------------------------------------------------------------------
# Mutation tests: We patch the transaction module-level reference so
# @transaction.atomic becomes a no-op.
# ---------------------------------------------------------------------------


class TestCreateCourse(_NoopAtomicMixin):
    """Tests for create_course mutation."""

    @patch("courses.services._mutations.Course")
    @patch("courses.services._mutations._teacher_profile_for")
    def test_creates_course_for_teacher(self, mock_tp_for, mock_course_model):
        """Creates course when teacher profile exists."""
        from courses.services._mutations import create_course

        fake_profile = SimpleNamespace(id=1)
        mock_tp_for.return_value = fake_profile
        fake_course = SimpleNamespace(id=100, name="NewCourse")
        mock_course_model.objects.create.return_value = fake_course

        result = create_course(SimpleNamespace(id=10), "NewCourse")

        assert result is fake_course
        mock_course_model.objects.create.assert_called_once_with(
            name="NewCourse", teacher_profile=fake_profile
        )

    @patch("courses.services._mutations._teacher_profile_for")
    def test_raises_when_no_teacher_profile(self, mock_tp_for):
        """Raises ValueError when user has no teacher profile."""
        from courses.services._mutations import create_course

        mock_tp_for.return_value = None

        with pytest.raises(ValueError, match="Teacher profile not found"):
            create_course(SimpleNamespace(id=10), "Course")


class TestEditCourse(_NoopAtomicMixin):
    """Tests for edit_course mutation."""

    def test_updates_course_name(self):
        """Updates course name and saves."""
        from courses.services._mutations import edit_course

        course = MagicMock()
        course.name = "Old Name"

        result = edit_course(course, "New Name")

        assert result.name == "New Name"
        course.save.assert_called_once_with(update_fields=["name"])


class TestDeleteCourse(_NoopAtomicMixin):
    """Tests for delete_course mutation."""

    def test_deletes_course(self):
        """Deletes course (enrollments cascade via Django)."""
        from courses.services._mutations import delete_course

        course = MagicMock()

        delete_course(course)

        course.delete.assert_called_once()


class TestCreateStudentInCourse(_NoopAtomicMixin):
    """Tests for create_student_in_course mutation."""

    @patch("courses.services._mutations.Course")
    def test_raises_when_course_not_found(self, mock_course_model):
        """Raises ValueError when course does not exist."""
        from courses.services._mutations import create_student_in_course

        mock_course_model.objects.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Course not found"):
            create_student_in_course(SimpleNamespace(id=1), 999, {"name": "S"})

    @patch("courses.services._mutations.Course")
    def test_rejects_client_supplied_username(self, mock_course_model):
        """Raises ValueError when client supplies a username."""
        from courses.services._mutations import create_student_in_course

        mock_course_model.objects.filter.return_value.first.return_value = SimpleNamespace(
            id=1, status="ACTIVE"
        )

        with pytest.raises(ValueError, match="system-managed"):
            create_student_in_course(
                SimpleNamespace(id=1), 1, {"name": "S", "username": "my-user"}
            )

    @patch("courses.services._mutations._create_submissions_for_student")
    @patch("courses.services._mutations.Enrollment")
    @patch("courses.services._mutations.StudentProfile")
    @patch("courses.services._mutations.create_user_from_payload")
    @patch("courses.services._mutations.generate_managed_username", return_value="stu12345")
    @patch("courses.services._mutations.Course")
    def test_raises_when_profile_not_created(
        self, mock_course_model, mock_gen, mock_create_user,
        mock_sp, mock_enroll, mock_subs
    ):
        """Raises ValueError when StudentProfile is not created."""
        from courses.services._mutations import create_student_in_course

        mock_course_model.objects.filter.return_value.first.return_value = SimpleNamespace(
            id=1, status="ACTIVE"
        )
        mock_create_user.return_value = SimpleNamespace(id=50)
        mock_sp.objects.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="StudentProfile not created"):
            create_student_in_course(SimpleNamespace(id=1), 1, {"name": "S"})

    @patch("courses.services._mutations._create_submissions_for_student")
    @patch("courses.services._mutations.Enrollment")
    @patch("courses.services._mutations.StudentProfile")
    @patch("courses.services._mutations.create_user_from_payload")
    @patch("courses.services._mutations.generate_managed_username", return_value="stu12345")
    @patch("courses.services._mutations.Course")
    def test_raises_when_already_enrolled(
        self, mock_course_model, mock_gen, mock_create_user,
        mock_sp, mock_enroll, mock_subs
    ):
        """Raises ValueError when student is already enrolled."""
        from courses.services._mutations import create_student_in_course

        mock_course_model.objects.filter.return_value.first.return_value = SimpleNamespace(
            id=1, status="ACTIVE"
        )
        mock_create_user.return_value = SimpleNamespace(id=50)
        fake_profile = SimpleNamespace(id=10, consent=False, save=MagicMock())
        mock_sp.objects.filter.return_value.first.return_value = fake_profile
        mock_enroll.objects.filter.return_value.exists.return_value = True

        with pytest.raises(ValueError, match="Student already enrolled"):
            create_student_in_course(SimpleNamespace(id=1), 1, {"name": "S"})

    @patch("courses.services._mutations._create_submissions_for_student")
    @patch("courses.services._mutations.Enrollment")
    @patch("courses.services._mutations.StudentProfile")
    @patch("courses.services._mutations.create_user_from_payload")
    @patch("courses.services._mutations.generate_managed_username", return_value="stu12345")
    @patch("courses.services._mutations.Course")
    def test_happy_path_creates_enrollment(
        self, mock_course_model, mock_gen, mock_create_user,
        mock_sp, mock_enroll, mock_subs
    ):
        """Happy path creates enrollment and returns it."""
        from courses.services._mutations import create_student_in_course

        fake_course = SimpleNamespace(id=1, status="ACTIVE")
        mock_course_model.objects.filter.return_value.first.return_value = fake_course
        student_user = SimpleNamespace(id=50)
        mock_create_user.return_value = student_user
        fake_profile = SimpleNamespace(id=10, consent=False, save=MagicMock())
        mock_sp.objects.filter.return_value.first.return_value = fake_profile
        mock_enroll.objects.filter.return_value.exists.return_value = False
        fake_enrollment = SimpleNamespace(id=100)
        mock_enroll.objects.create.return_value = fake_enrollment

        result = create_student_in_course(
            SimpleNamespace(id=1), 1, {"name": "Student", "consent": True}
        )

        assert result is fake_enrollment
        mock_enroll.objects.create.assert_called_once_with(
            course=fake_course, student_profile=fake_profile, status=EnrollmentStatus.ACTIVE
        )
        assert fake_profile.consent is True
        mock_subs.assert_called_once_with(student_user, fake_course)


class TestRemoveStudentFromCourse(_NoopAtomicMixin):
    """Tests for remove_student_from_course mutation."""

    @patch("courses.services._mutations.StudentProfile")
    def test_raises_when_profile_not_found(self, mock_sp_model):
        """Raises ValueError when student profile does not exist."""
        from courses.services._mutations import remove_student_from_course

        mock_sp_model.objects.filter.return_value.first.return_value = None
        course = SimpleNamespace(id=1, status="ACTIVE")

        with pytest.raises(ValueError, match="Student not found in course"):
            remove_student_from_course(course, 999)

    @patch("courses.services._mutations.Enrollment")
    @patch("courses.services._mutations.StudentProfile")
    def test_drops_enrollment(self, mock_sp_model, mock_enrollment_model):
        """Soft-deletes enrollment by setting status to DROPPED."""
        from courses.services._mutations import remove_student_from_course

        fake_profile = SimpleNamespace(id=10)
        mock_sp_model.objects.filter.return_value.first.return_value = fake_profile
        fake_enrollment = MagicMock()
        mock_enrollment_model.objects.filter.return_value.first.return_value = fake_enrollment

        course = SimpleNamespace(id=1, status="ACTIVE")
        remove_student_from_course(course, 42)

        assert fake_enrollment.status == EnrollmentStatus.DROPPED
        fake_enrollment.save.assert_called_once_with(update_fields=["status"])


# ---------------------------------------------------------------------------
# _create_submissions_for_student (internal, not decorated with @transaction.atomic)
# ---------------------------------------------------------------------------


class TestCreateSubmissionsForStudent:
    """Tests for _create_submissions_for_student internal helper."""

    @patch("courses.services._mutations.Assignment")
    @patch("courses.services._mutations.Assessment")
    def test_skips_when_assessment_not_found(self, mock_assessment_model, mock_assignment_model):
        """Skips when assessment does not exist."""
        from courses.services._mutations import _create_submissions_for_student

        fake_assignment = SimpleNamespace(id=1, assessment_id=99)
        mock_assignment_model.objects.filter.return_value = [fake_assignment]
        mock_assessment_model.objects.filter.return_value.first.return_value = None

        _create_submissions_for_student(SimpleNamespace(id=1), SimpleNamespace(id=1))

    @patch("courses.services._mutations.NumberScaleAnswer")
    @patch("courses.services._mutations.ShortAnswerAnswer")
    @patch("courses.services._mutations.MultipleChoiceAnswer")
    @patch("courses.services._mutations.Answer")
    @patch("courses.services._mutations.Submission")
    @patch("courses.services._mutations.Assessment")
    @patch("courses.services._mutations.Assignment")
    @patch("courses.services._mutations.answer_type_from_question")
    def test_creates_submissions_with_answers(
        self, mock_answer_type, mock_assignment_model, mock_assessment_model,
        mock_submission_model, mock_answer_model, mock_mca, mock_saa, mock_nsa,
    ):
        """Creates submission with correct answer types for each question kind."""
        from assessments.models import QuestionKind
        from courses.services._mutations import _create_submissions_for_student

        fake_assignment = SimpleNamespace(id=1, assessment_id=10)
        mock_assignment_model.objects.filter.return_value = [fake_assignment]

        mc_q = SimpleNamespace(kind=QuestionKind.MULTIPLE_CHOICE)
        sa_q = SimpleNamespace(kind=QuestionKind.SHORT_ANSWER)
        ns_q = SimpleNamespace(kind=QuestionKind.NUMBER_SCALE)

        fake_assessment = MagicMock()
        fake_assessment.id = 10
        fake_assessment.questions.all.return_value = [mc_q, sa_q, ns_q]
        mock_assessment_model.objects.filter.return_value.first.return_value = fake_assessment
        mock_submission_model.objects.filter.return_value.exists.return_value = False
        mock_submission_model.objects.create.return_value = SimpleNamespace(id=100)
        mock_answer_type.return_value = "MC"
        mock_answer_model.objects.create.return_value = SimpleNamespace(id=200)

        _create_submissions_for_student(SimpleNamespace(id=1), SimpleNamespace(id=5))

        mock_submission_model.objects.create.assert_called_once()
        assert mock_answer_model.objects.create.call_count == 3
        mock_mca.objects.create.assert_called_once()
        mock_saa.objects.create.assert_called_once()
        mock_nsa.objects.create.assert_called_once()
