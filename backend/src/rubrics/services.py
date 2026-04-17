"""Rubric domain helpers."""

from django.db import transaction

from accounts.models import User
from core.dtos import RubricCriterionDTO, RubricDTO, RubricLevelDTO

from .models import Rubric, RubricCriterion, RubricLevel, RubricStatus


class RubricReferencedError(Exception):
    """Raised when a mutation is blocked because questions/groups reference the rubric."""


def _rubric_with_related(rubric_id: int) -> Rubric | None:
    """Fetch a rubric with criteria and levels prefetched for DTO conversion."""
    from django.db.models import Prefetch

    return (
        Rubric.objects.filter(id=rubric_id)
        .prefetch_related(
            Prefetch(
                "criteria",
                queryset=RubricCriterion.objects.order_by("order_index"),
            ),
            Prefetch(
                "criteria__levels",
                queryset=RubricLevel.objects.order_by("order_index"),
            ),
        )
        .first()
    )


def rubric_to_dto(rubric: Rubric) -> RubricDTO:
    """Convert a Rubric model instance to a RubricDTO with nested criteria and levels.

    For best performance, pass a rubric loaded via _rubric_with_related() or
    from list_rubrics() so that criteria and levels are prefetched.
    """
    criteria = []
    # When prefetched with ordered Prefetch objects, .all() preserves order.
    for criterion in rubric.criteria.all():
        levels = [
            RubricLevelDTO(
                id=level.id,
                label=level.label,
                points=level.points,
                description=level.description,
                orderIndex=level.order_index,
            )
            for level in criterion.levels.all()
        ]
        criteria.append(
            RubricCriterionDTO(
                id=criterion.id,
                title=criterion.title,
                description=criterion.description,
                orderIndex=criterion.order_index,
                weight=criterion.weight,
                levels=levels,
            )
        )
    return RubricDTO(
        id=rubric.id,
        title=rubric.title,
        description=rubric.description,
        status=rubric.status,
        createdBy=rubric.created_by_id,
        createdAt=rubric.created_at,
        updatedAt=rubric.updated_at,
        criteria=criteria,
    )


def list_rubrics() -> list[Rubric]:
    """Return all rubrics with criteria and levels prefetched."""
    from django.db.models import Prefetch

    return list(
        Rubric.objects.prefetch_related(
            Prefetch(
                "criteria",
                queryset=RubricCriterion.objects.order_by("order_index"),
            ),
            Prefetch(
                "criteria__levels",
                queryset=RubricLevel.objects.order_by("order_index"),
            ),
        ).all()
    )


@transaction.atomic
def create_rubric(request_user: User, payload: dict) -> Rubric:
    """Create a new rubric with optional criteria and levels.

    Args:
        request_user: The user creating the rubric (set as created_by).
        payload: Dict with 'title', optional 'description' and 'criteria'.

    Raises:
        ValueError: If title is missing or a criterion/level lacks required fields.
    """
    title = payload.get("title")
    if not title:
        raise ValueError("title is required")

    rubric = Rubric.objects.create(
        title=title,
        description=payload.get("description", ""),
        created_by=request_user,
    )
    _replace_criteria(rubric, payload.get("criteria") or [])
    return rubric


@transaction.atomic
def update_rubric(rubric: Rubric, payload: dict) -> Rubric:
    """Update a rubric's title, description, and/or criteria.

    Raises:
        RubricReferencedError: If the rubric is referenced by assignment template questions.
    """
    if _is_referenced(rubric):
        raise RubricReferencedError("Cannot update rubric referenced by assignment templates")

    rubric.title = payload.get("title", rubric.title)
    rubric.description = payload.get("description", rubric.description)
    rubric.save()
    if "criteria" in payload:
        _replace_criteria(rubric, payload["criteria"])
    return rubric


@transaction.atomic
def delete_rubric(rubric: Rubric) -> None:
    """Hard-delete a rubric. Blocked if referenced by assignment template questions."""
    if _is_referenced(rubric):
        raise RubricReferencedError("Cannot delete rubric referenced by assignment templates")
    rubric.delete()


@transaction.atomic
def archive_rubric(rubric: Rubric) -> Rubric:
    """Set rubric status to ARCHIVED. Raises ValueError if already archived."""
    if rubric.status == RubricStatus.ARCHIVED:
        raise ValueError("Rubric is already archived")
    rubric.status = RubricStatus.ARCHIVED
    rubric.save(update_fields=["status"])
    return rubric


def _is_referenced(rubric: Rubric) -> bool:
    """Check if any questions or question groups reference this rubric."""
    from assignment_templates.models import AssignmentTemplateQuestionGroup, Question

    if Question.objects.filter(rubric=rubric).exists():
        return True
    if AssignmentTemplateQuestionGroup.objects.filter(rubric=rubric).exists():
        return True
    return False


def _replace_criteria(rubric: Rubric, criteria: list[dict]) -> None:
    RubricCriterion.objects.filter(rubric=rubric).delete()
    for idx, crit_payload in enumerate(criteria):
        title = crit_payload.get("title")
        if not title:
            raise ValueError(f"Criterion at index {idx} requires a title")
        criterion = RubricCriterion.objects.create(
            rubric=rubric,
            title=title,
            description=crit_payload.get("description", ""),
            order_index=crit_payload.get("orderIndex", idx),
            weight=crit_payload.get("weight", 1.0),
        )
        levels = crit_payload.get("levels") or []
        for level_idx, level_payload in enumerate(levels):
            label = level_payload.get("label")
            if not label:
                raise ValueError(
                    f"Level at index {level_idx} of criterion '{title}' requires a label"
                )
            RubricLevel.objects.create(
                criterion=criterion,
                label=label,
                points=level_payload.get("points", 0),
                description=level_payload.get("description", ""),
                order_index=level_payload.get("orderIndex", level_idx),
            )
