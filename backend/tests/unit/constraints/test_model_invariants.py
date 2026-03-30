"""Database-level constraint tests for model invariants (Phase 3).

These tests verify that CheckConstraints on Assignment and Submission models
reject invalid rows at the database boundary.
"""

import pytest
from django.db import IntegrityError

from assignments.models import Assignment, AudienceType
from submissions.models import Submission, SubmissionStatus
from tests.factories import (
    AssessmentFactory,
    AssignmentFactory,
    CourseFactory,
    SubmissionFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# 3a. Assignment audience/course CheckConstraint
# ---------------------------------------------------------------------------


class TestAssignmentAudienceCourseConstraint:
    """COURSE assignments must have a course; TEACHER assignments must not."""

    def test_course_assignment_with_course_succeeds(self):
        """COURSE audience_type with a course FK is valid."""
        assignment = AssignmentFactory(
            audience_type=AudienceType.COURSE,
            course=CourseFactory(),
        )
        assert assignment.pk is not None

    def test_course_assignment_without_course_rejected(self):
        """COURSE audience_type with null course violates constraint."""
        with pytest.raises(IntegrityError):
            AssignmentFactory(
                audience_type=AudienceType.COURSE,
                course=None,
            )

    def test_teacher_assignment_without_course_succeeds(self):
        """TEACHER audience_type with null course is valid."""
        user = UserFactory()
        assignment = AssignmentFactory(
            audience_type=AudienceType.TEACHER,
            course=None,
            teacher=user,
        )
        assert assignment.pk is not None

    def test_teacher_assignment_with_course_rejected(self):
        """TEACHER audience_type with a course FK violates constraint."""
        user = UserFactory()
        with pytest.raises(IntegrityError):
            AssignmentFactory(
                audience_type=AudienceType.TEACHER,
                course=CourseFactory(),
                teacher=user,
            )


# ---------------------------------------------------------------------------
# 3b. Submission owner XOR CheckConstraint
# ---------------------------------------------------------------------------


class TestSubmissionOwnerXorConstraint:
    """Exactly one of student or teacher must be set on a submission."""

    def test_student_only_succeeds(self):
        """Submission with student and no teacher is valid."""
        sub = SubmissionFactory(student=UserFactory(), teacher=None)
        assert sub.pk is not None

    def test_teacher_only_succeeds(self):
        """Submission with teacher and no student is valid."""
        sub = SubmissionFactory(student=None, teacher=UserFactory())
        assert sub.pk is not None

    def test_both_student_and_teacher_rejected(self):
        """Submission with both student and teacher violates constraint."""
        with pytest.raises(IntegrityError):
            SubmissionFactory(student=UserFactory(), teacher=UserFactory())

    def test_neither_student_nor_teacher_rejected(self):
        """Submission with neither student nor teacher violates constraint."""
        with pytest.raises(IntegrityError):
            SubmissionFactory(student=None, teacher=None)
