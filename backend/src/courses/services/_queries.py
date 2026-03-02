"""
Course and student domain queries — read-only helpers and DTOs.
"""

from accounts.models import Role, StudentProfile, TeacherProfile, User
from assignments.models import Assignment
from core.dtos import CourseDTO, EnrollmentStudentDTO
from core.permissions import has_role

from ..models import Course, Enrollment, EnrollmentStatus


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

    Admins (is_staff) can view all courses.
    Researchers can view all courses (for data oversight).
    Teachers can only view their own courses.
    """
    if request_user.is_staff:
        return True
    if has_role(request_user, Role.RESEARCHER):
        return True
    owner = _course_owner(course)
    return owner is not None and owner.id == request_user.id


def can_manage_course(request_user: User, course: Course) -> bool:
    """Check if a user can manage (edit/delete) a course. Only the course owner can."""
    owner = _course_owner(course)
    return owner is not None and owner.id == request_user.id


def course_to_dto(course: Course) -> CourseDTO:
    """Convert a Course to a DTO with enrolled students and assignment IDs."""
    enrollments = Enrollment.objects.filter(course=course, status=EnrollmentStatus.ACTIVE)
    students = [enrollment_to_student_dto(e) for e in enrollments]
    assignment_ids = list(Assignment.objects.filter(course=course).values_list("id", flat=True))
    teacher_user = course.teacher_profile.user if course.teacher_profile else None
    return CourseDTO(
        id=course.id,
        name=course.name,
        students=students,
        studentCount=len(students),
        assignmentIds=assignment_ids,
        teacherId=course.teacher_profile_id,
        teacherName=teacher_user.name if teacher_user else None,
        createdAt=course.created_at,
    )


def enrollment_to_student_dto(enrollment: Enrollment) -> EnrollmentStudentDTO:
    """Convert an Enrollment to a student DTO with user info and consent status."""
    student_profile = enrollment.student_profile
    user = student_profile.user if student_profile else None
    return EnrollmentStudentDTO(
        id=user.id if user else None,
        name=user.name if user else None,
        username=user.username if user else None,
        role="STUDENT",
        consent=bool(student_profile.consent) if student_profile else False,
        courseId=enrollment.course_id,
        enrolledAt=enrollment.enrolled_at,
    )


def list_courses_for_user(user: User) -> list[Course]:
    """
    List courses accessible to a user.

    Admins (is_staff) see all courses.
    Researchers see all courses (for data oversight).
    Teachers see only their own courses.
    Students see only courses they are enrolled in.
    """
    if user.is_staff:
        return list(Course.objects.all())
    if has_role(user, Role.RESEARCHER):
        return list(Course.objects.all())
    if has_role(user, Role.STUDENT):
        profile = StudentProfile.objects.filter(user=user).first()
        if not profile:
            return []
        return list(Course.objects.filter(enrollments__student_profile=profile).distinct())
    return list(Course.objects.filter(teacher_profile__user=user))


def list_students_in_course(course: Course) -> list[EnrollmentStudentDTO]:
    """Return all students enrolled in a course as DTOs."""
    enrollments = Enrollment.objects.filter(course=course, status=EnrollmentStatus.ACTIVE)
    return [enrollment_to_student_dto(e) for e in enrollments]
