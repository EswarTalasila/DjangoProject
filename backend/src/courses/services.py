"""
Course and student domain helpers.

This module provides business logic for course management including:
- Course CRUD operations
- Student enrollment and removal
- Permission checks for course access
- Automatic submission creation when students are enrolled

Enrollment flow:
1. Teacher creates a course
2. Teacher adds students to the course
3. System creates placeholder submissions for existing assignments
4. Students can then access and complete their submissions
"""

import logging

from django.db import transaction

from accounts.models import Role, StudentProfile, TeacherProfile, User
from accounts.services import create_user_from_payload
from assessments.models import Assessment, QuestionKind
from assignments.models import Assignment
from core.dtos import CourseDTO, EnrollmentStudentDTO
from core.permissions import has_role
from submissions.models import (
    Answer,
    AnswerType,
    MultipleChoiceAnswer,
    NumberScaleAnswer,
    ShortAnswerAnswer,
    Submission,
    SubmissionStatus,
)

from .models import Course, Enrollment, EnrollmentStatus

logger = logging.getLogger(__name__)


def _teacher_profile_for(user: User) -> TeacherProfile | None:
    """Get the TeacherProfile for a user, or None if not a teacher."""
    return TeacherProfile.objects.filter(user=user).first()


def _course_owner(course: Course) -> User | None:
    """Get the User who owns (teaches) a course."""
    if not course.teacher_profile:
        return None
    return course.teacher_profile.user


def can_view_course(request_user: User, course: Course) -> bool:
    """
    Check if a user can view a course.

    Admins can view all courses. Teachers can only view their own courses.
    """
    if has_role(request_user, Role.ADMIN):
        return True
    owner = _course_owner(course)
    return owner is not None and owner.id == request_user.id


def can_manage_course(request_user: User, course: Course) -> bool:
    """Check if a user can manage (edit/delete) a course. Only the course owner can."""
    owner = _course_owner(course)
    return owner is not None and owner.id == request_user.id


def course_to_dto(course: Course) -> CourseDTO:
    """
    Convert a Course to a DTO with enrolled students and assignment IDs.

    Returns:
        CourseDTO with id, name, students, studentCount, assignmentIds, teacherId
    """
    enrollments = Enrollment.objects.filter(course=course)
    students = [enrollment_to_student_dto(e) for e in enrollments]
    assignment_ids = list(Assignment.objects.filter(course=course).values_list("id", flat=True))
    return CourseDTO(
        id=course.id,
        name=course.name,
        students=students,
        studentCount=len(students),
        assignmentIds=assignment_ids,
        teacherId=course.teacher_profile_id,
    )


def enrollment_to_student_dto(enrollment: Enrollment) -> EnrollmentStudentDTO:
    """Convert an Enrollment to a student DTO with user info and consent status."""
    student_profile = enrollment.student_profile
    user = student_profile.user if student_profile else None
    return EnrollmentStudentDTO(
        id=user.id if user else None,
        name=user.name if user else None,
        username=user.username if user else None,
        role="ROLE_STUDENT",
        consent=bool(student_profile.consent) if student_profile else False,
        courseId=enrollment.course_id,
    )


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
    Delete a course and all associated students.

    This performs a hard delete of the course, all enrollments, and all
    student users who were enrolled. Consider implementing soft delete
    for audit purposes.
    """
    enrollments = Enrollment.objects.filter(course=course)
    student_user_ids = list(enrollments.values_list("student_profile__user_id", flat=True))
    enrollments.delete()
    User.objects.filter(id__in=student_user_ids).delete()
    course.delete()


def list_courses_for_user(user: User) -> list[Course]:
    """
    List courses accessible to a user.

    Admins see all courses. Teachers see only their own courses.
    """
    if has_role(user, Role.ADMIN):
        return list(Course.objects.all())
    return list(Course.objects.filter(teacher_profile__user=user))


@transaction.atomic
def create_student_in_course(request_user: User, payload: dict) -> Enrollment:
    """
    Create a new student and enroll them in a course.

    This is the main entry point for adding students. It:
    1. Creates the student user account
    2. Creates/updates the student profile with consent status
    3. Creates the enrollment record
    4. Creates placeholder submissions for all existing course assignments

    Args:
        request_user: The teacher adding the student
        payload: Dict with name, username, courseId, and optionally consent

    Returns:
        The created Enrollment

    Raises:
        ValueError: If course not found, profile creation failed, or student already enrolled
    """
    course_id = payload.get("courseId")
    if course_id is None:
        raise ValueError("courseId is required")
    course = Course.objects.filter(id=course_id).first()
    if not course:
        raise ValueError("Course not found")

    student_user = create_user_from_payload(
        payload, role_override=Role.STUDENT, creator=request_user
    )
    student_profile = StudentProfile.objects.filter(user=student_user).first()
    if not student_profile:
        raise ValueError("StudentProfile not created")

    consent = payload.get("consent")
    if consent is not None:
        student_profile.consent = consent
        student_profile.save(update_fields=["consent"])

    if Enrollment.objects.filter(student_profile=student_profile).exists():
        raise ValueError("Student already enrolled in a course")

    enrollment = Enrollment.objects.create(
        course=course, student_profile=student_profile, status=EnrollmentStatus.ACTIVE
    )

    _create_submissions_for_student(student_user, course)
    return enrollment


@transaction.atomic
def bulk_create_students(request_user: User, payloads: list[dict]) -> int:
    """
    Create multiple students in bulk. Errors are silently ignored.

    Returns:
        The number of students successfully created
    """
    created = 0
    for payload in payloads:
        try:
            create_student_in_course(request_user, payload)
            created += 1
        except Exception:
            logger.exception("Bulk create student failed for payload.")
            continue
    return created


@transaction.atomic
def remove_student_from_course(course: Course, student_user_id: int) -> None:
    """
    Remove a student from a course and delete their user account.

    Note: This is a hard delete. The student user is completely removed.
    """
    student_profile = StudentProfile.objects.filter(user_id=student_user_id).first()
    if not student_profile:
        raise ValueError("Student profile not found")
    Enrollment.objects.filter(course=course, student_profile=student_profile).delete()
    User.objects.filter(id=student_user_id).delete()


def list_students_in_course(course: Course) -> list[EnrollmentStudentDTO]:
    """Return all students enrolled in a course as DTOs."""
    enrollments = Enrollment.objects.filter(course=course)
    return [enrollment_to_student_dto(e) for e in enrollments]


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
        if assessment.grading_mode == "MOOD_METER":
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
                answer_type=_answer_type_from_question(question),
                score=0.0,
                skipped=False,
            )
            if question.kind == QuestionKind.MULTIPLE_CHOICE:
                MultipleChoiceAnswer.objects.create(answer=answer)
            elif question.kind == QuestionKind.SHORT_ANSWER:
                ShortAnswerAnswer.objects.create(answer=answer, text="")
            elif question.kind == QuestionKind.NUMBER_SCALE:
                NumberScaleAnswer.objects.create(answer=answer, val=None)


def _answer_type_from_question(question) -> str:
    """Map a question kind to the corresponding answer type."""
    if question.kind == QuestionKind.MULTIPLE_CHOICE:
        return AnswerType.MULTIPLE_CHOICE
    if question.kind == QuestionKind.SHORT_ANSWER:
        return AnswerType.SHORT_ANSWER
    if question.kind == QuestionKind.NUMBER_SCALE:
        return AnswerType.NUMBER_SCALE
    if question.kind == QuestionKind.MOOD_METER:
        return AnswerType.MOOD_METER
    return AnswerType.SHORT_ANSWER
