"""Unit tests for RegistrationCode.clean() course-binding invariant.

STUDENT registration codes must reference a course. Non-student codes
(TEACHER, RESEARCHER) do not require a course.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.unit


class TestRegistrationCodeCourseBinding:
    """STUDENT codes require a course FK; others do not."""

    def _make_code(self, code_type, course_id=None):
        from accounts.models import RegistrationCode

        code = RegistrationCode()
        code.code_type = code_type
        code.course_id = course_id
        code.max_uses = 1
        code.times_used = 0
        return code

    def test_student_code_without_course_fails(self):
        """STUDENT code with null course_id raises ValidationError."""
        code = self._make_code("STUDENT", course_id=None)
        with pytest.raises(ValidationError, match="course"):
            code.clean()

    def test_student_code_with_course_passes(self):
        """STUDENT code with a course_id passes clean()."""
        code = self._make_code("STUDENT", course_id=42)
        code.clean()  # should not raise

    def test_teacher_code_without_course_passes(self):
        """TEACHER code without a course is valid."""
        code = self._make_code("TEACHER", course_id=None)
        code.clean()  # should not raise

    def test_researcher_code_without_course_passes(self):
        """RESEARCHER code without a course is valid."""
        code = self._make_code("RESEARCHER", course_id=None)
        code.clean()  # should not raise

    def test_teacher_code_with_course_fails(self):
        """TEACHER code with a course violates the course-binding invariant."""
        code = self._make_code("TEACHER", course_id=42)
        with pytest.raises(ValidationError, match="Only student"):
            code.clean()

    def test_researcher_code_with_course_fails(self):
        """RESEARCHER code with a course violates the course-binding invariant."""
        code = self._make_code("RESEARCHER", course_id=42)
        with pytest.raises(ValidationError, match="Only student"):
            code.clean()
