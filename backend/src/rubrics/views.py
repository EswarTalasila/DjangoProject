"""Rubric management API endpoints."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.errors import error_response
from core.pagination import paginate
from core.permissions import IsResearcherOrAdmin, IsTeacherOrAbove

from .models import Rubric
from .serializers import RubricSerializer
from .services import (
    RubricReferencedError,
    _rubric_with_related,
    archive_rubric,
    create_rubric,
    delete_rubric,
    list_rubrics,
    rubric_to_dto,
    update_rubric,
)


@api_view(["GET", "POST"])
@permission_classes([IsTeacherOrAbove])
def list_or_create(request):
    if request.method == "POST":
        if not IsResearcherOrAdmin().has_permission(request, None):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = RubricSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            rubric = create_rubric(request.user, serializer.validated_data)
        except ValueError as exc:
            return error_response(exc)
        return Response(rubric_to_dto(rubric).model_dump(), status=status.HTTP_201_CREATED)

    rubrics = list_rubrics()
    return paginate(rubrics, request, transform_fn=lambda r: rubric_to_dto(r).model_dump())


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsTeacherOrAbove])
def detail(request, rubric_id: int):
    rubric = Rubric.objects.filter(id=rubric_id).first()
    if not rubric:
        return Response({"detail": "Rubric not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        # Re-fetch with prefetched criteria/levels for efficient DTO serialization.
        rubric = _rubric_with_related(rubric_id)
        return Response(rubric_to_dto(rubric).model_dump(), status=status.HTTP_200_OK)

    if request.method == "PATCH":
        if not IsResearcherOrAdmin().has_permission(request, None):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = RubricSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = update_rubric(rubric, serializer.validated_data)
        except RubricReferencedError as exc:
            return error_response(exc, status_code=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return error_response(exc)
        return Response(rubric_to_dto(updated).model_dump(), status=status.HTTP_200_OK)

    if not IsResearcherOrAdmin().has_permission(request, None):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        delete_rubric(rubric)
    except RubricReferencedError as exc:
        return error_response(exc, status_code=status.HTTP_409_CONFLICT)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsTeacherOrAbove])
def archive(request, rubric_id: int):
    if not IsResearcherOrAdmin().has_permission(request, None):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    rubric = Rubric.objects.filter(id=rubric_id).first()
    if not rubric:
        return Response({"detail": "Rubric not found"}, status=status.HTTP_404_NOT_FOUND)
    try:
        archived = archive_rubric(rubric)
    except ValueError as exc:
        return error_response(exc, status_code=status.HTTP_409_CONFLICT)
    return Response(rubric_to_dto(archived).model_dump(), status=status.HTTP_200_OK)
