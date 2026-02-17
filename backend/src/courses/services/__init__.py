"""
Course and student domain helpers — re-exported from sub-modules.
"""

from ._mutations import (
    _create_submissions_for_student,
    bulk_create_students,
    create_course,
    create_student_in_course,
    delete_course,
    edit_course,
    remove_student_from_course,
)
from ._queries import (
    _course_owner,
    _teacher_profile_for,
    can_manage_course,
    can_view_course,
    course_to_dto,
    enrollment_to_student_dto,
    list_courses_for_user,
    list_students_in_course,
)

__all__ = [
    "_course_owner",
    "_create_submissions_for_student",
    "_teacher_profile_for",
    "bulk_create_students",
    "can_manage_course",
    "can_view_course",
    "course_to_dto",
    "create_course",
    "create_student_in_course",
    "delete_course",
    "edit_course",
    "enrollment_to_student_dto",
    "list_courses_for_user",
    "list_students_in_course",
    "remove_student_from_course",
]
