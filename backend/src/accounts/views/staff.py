"""Staff and student listing views."""

import sys

from django.db.models import Exists, OuterRef, Prefetch, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from courses.models import Enrollment, EnrollmentStatus


def _v():
    return sys.modules["accounts.views"]


@api_view(["GET"])
@permission_classes([_v().IsResearcherOrAdmin])
def list_staff(request):
    """List staff directory users (researchers and teachers)."""
    v = _v()
    users = (
        v.User.objects.filter(roles__role__in=[v.Role.TEACHER, v.Role.RESEARCHER])
        .prefetch_related("roles")
        .distinct()
        .order_by("id")
    )
    return v.paginate(users, request, transform_fn=lambda u: v.UserOutputSerializer(u).data)


@api_view(["GET"])
@permission_classes([_v().IsResearcherOrAdmin])
def list_students(request):
    """List student users with their active course enrollments."""
    v = _v()
    course_id_param = request.query_params.get("courseId")
    if course_id_param is not None:
        try:
            course_id = int(course_id_param)
            if course_id < 1:
                raise ValueError
        except (ValueError, TypeError):
            return v.error_response("courseId must be a positive integer", status_code=400)
    else:
        course_id = None

    active_enrollment_exists = Enrollment.objects.filter(
        student_profile__user=OuterRef("pk"),
        status=EnrollmentStatus.ACTIVE,
    )

    users = (
        v.User.objects.filter(roles__role=v.Role.STUDENT)
        .filter(Exists(active_enrollment_exists))
        .prefetch_related(
            Prefetch(
                "student_profile__enrollments",
                queryset=Enrollment.objects.filter(
                    status=EnrollmentStatus.ACTIVE,
                ).select_related("course"),
                to_attr="active_enrollments",
            ),
        )
        .distinct()
        .order_by("id")
    )

    search = request.query_params.get("q", "").strip()
    if search:
        users = users.filter(Q(name__icontains=search) | Q(username__icontains=search))

    if course_id is not None:
        users = users.filter(
            student_profile__enrollments__course_id=course_id,
            student_profile__enrollments__status=EnrollmentStatus.ACTIVE,
        )

    def transform(user):
        enrollments = getattr(user.student_profile, "active_enrollments", [])
        return v.StudentListSerializer(
            {
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "courses": [
                    {"id": e.course.id, "name": e.course.name} for e in enrollments
                ],
            }
        ).data

    return v.paginate(users, request, transform_fn=transform)
