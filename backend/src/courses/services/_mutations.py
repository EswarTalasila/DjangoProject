"""
Course and student domain mutations — create, edit, and delete operations.
"""

import logging

from django.db import transaction

from accounts.models import Role, StudentProfile, User
from accounts.services import create_user_from_payload, generate_managed_username
from assessments.models import Assessment, GradingMode, QuestionKind
from assignments.models import Assignment
from core.helpers import answer_type_from_question
from submissions.models import (
    Answer,
    MultipleChoiceAnswer,
    NumberScaleAnswer,
    ShortAnswerAnswer,
    Submission,
    SubmissionStatus,
)

from ..models import Course, Enrollment, EnrollmentStatus
from ._queries import _teacher_profile_for

logger = logging.getLogger(__name__)


@transaction.atomic
def create_course(request_user: User, name: str) -> Course:
    """
    Create a new course owned by the given teacher.

    Args:
        request_user: The teacher creating the course
        name: The course name

    Returns:
        The created Course

    Raises:
        ValueError: If the user doesn't have a teacher profile
    """
    teacher_profile = _teacher_profile_for(request_user)
    if not teacher_profile:
        raise ValueError("Teacher profile not found")
    return Course.objects.create(name=name, teacher_profile=teacher_profile)


@transaction.atomic
def edit_course(course: Course, name: str) -> Course:
    """Update a course's name."""
    course.name = name
    course.save(update_fields=["name"])
    return course


@transaction.atomic
def delete_course(course: Course) -> None:
    """
    Delete a course and its enrollments.

    Enrollment records are cascade-deleted by Django. Student User
    accounts are intentionally preserved (CRS-CN-05).
    """
    course.delete()


@transaction.atomic
def create_student_in_course(request_user: User, course_id: int, payload: dict) -> Enrollment:
    """
    Create a new student and enroll them in a course.

    Args:
        request_user: The teacher adding the student
        course_id: ID of the course to enroll into (from URL path)
        payload: Dict with name, and optionally consent and password

    Returns:
        The created Enrollment

    Raises:
        ValueError: If course not found, profile creation failed, or student already enrolled
    """
    course = Course.objects.filter(id=course_id).first()
    if not course:
        raise ValueError("Course not found")

    raw_username = str(payload.get("username", "")).strip()
    if raw_username:
        raise ValueError("username is system-managed and must not be provided")

    create_payload = dict(payload)
    create_payload["username"] = generate_managed_username(name=payload.get("name"))
    student_user = create_user_from_payload(
        create_payload, role_override=Role.STUDENT, creator=request_user
    )
    student_profile = StudentProfile.objects.filter(user=student_user).first()
    if not student_profile:
        raise ValueError("StudentProfile not created")

    consent = payload.get("consent")
    if consent is not None:
        student_profile.consent = consent
        student_profile.save(update_fields=["consent"])

    if Enrollment.objects.filter(course=course, student_profile=student_profile).exists():
        raise ValueError("Student already enrolled in this course")

    enrollment = Enrollment.objects.create(
        course=course, student_profile=student_profile, status=EnrollmentStatus.ACTIVE
    )

    _create_submissions_for_student(student_user, course)
    return enrollment


@transaction.atomic
def remove_student_from_course(course: Course, student_user_id: int) -> None:
    """
    Remove a student from a course by setting enrollment to DROPPED.

    The student User account is preserved (CRS-CN-05). Already-DROPPED
    enrollments are treated as not found (CRS-UC-08-E2).
    """
    student_profile = StudentProfile.objects.filter(user_id=student_user_id).first()
    if not student_profile:
        raise ValueError("Student not found in course")
    enrollment = Enrollment.objects.filter(
        course=course, student_profile=student_profile, status=EnrollmentStatus.ACTIVE
    ).first()
    if not enrollment:
        raise ValueError("Student not found in course")
    enrollment.status = EnrollmentStatus.DROPPED
    enrollment.save(update_fields=["status"])


def _create_submissions_for_student(student_user: User, course: Course) -> None:
    """
    Create placeholder submissions for all existing course assignments.

    When a student is enrolled, they need submission records for assignments
    that were already created. This creates NOT_STARTED submissions with
    empty answers for each non-MOOD_METER assignment in the course.
    """
    assignments = Assignment.objects.filter(course=course)
    for assignment in assignments:
        assessment = Assessment.objects.filter(id=assignment.assessment_id).first()
        if not assessment:
            continue
        if assessment.grading_mode == GradingMode.MOOD_METER:
            continue
        if Submission.objects.filter(student=student_user, assignment=assignment).exists():
            continue

        submission = Submission.objects.create(
            assignment=assignment,
            student=student_user,
            teacher=None,
            submitted_at=None,
            status=SubmissionStatus.NOT_STARTED,
        )

        for question in assessment.questions.all():
            if question.kind == QuestionKind.MOOD_METER:
                continue
            answer = Answer.objects.create(
                submission=submission,
                question=question,
                answer_type=answer_type_from_question(question),
                score=0.0,
                skipped=False,
            )
            if question.kind == QuestionKind.MULTIPLE_CHOICE:
                MultipleChoiceAnswer.objects.create(answer=answer)
            elif question.kind == QuestionKind.SHORT_ANSWER:
                ShortAnswerAnswer.objects.create(answer=answer, text="")
            elif question.kind == QuestionKind.NUMBER_SCALE:
                NumberScaleAnswer.objects.create(answer=answer, val=None)
