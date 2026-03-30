"""Assessment domain helpers."""

from collections.abc import Iterable

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from assignments.models import Assignment
from core.dtos import AssessmentDTO, QuestionDTO, QuestionGroupDTO

from core.lifecycle import ConflictError

from .models import (
    Assessment,
    AssessmentQuestionGroup,
    AssessmentStatus,
    GradingMode,
    GradingStrategy,
    McqChoice,
    MultipleChoiceQuestion,
    NumberScaleQuestion,
    Question,
    QuestionKind,
    ScoringPolicy,
    ShortAnswerQuestion,
)


class AssessmentReferencedError(Exception):
    """Raised when a mutation is blocked because assignments reference the assessment."""


def _assessment_with_related(assessment_id: int) -> Assessment | None:
    """Fetch an assessment with all related data prefetched for DTO conversion."""
    return (
        Assessment.objects.filter(id=assessment_id)
        .prefetch_related(
            "question_groups",
            "questions__mcq_choices",
            "questions__multiple_choice",
            "questions__short_answer",
            "questions__number_scale",
        )
        .first()
    )


def assessment_to_dto(assessment: Assessment) -> AssessmentDTO:
    """Convert an Assessment to a DTO.

    For best performance, pass an assessment loaded via _assessment_with_related()
    so that question_groups, questions and their sub-types are prefetched.
    """
    groups = []
    for g in assessment.question_groups.all().order_by("order_index"):
        groups.append(
            QuestionGroupDTO(
                id=g.id,
                name=g.name,
                rubricId=g.rubric_id,
                orderIndex=g.order_index,
            )
        )
    return AssessmentDTO(
        id=assessment.id,
        title=assessment.title,
        category=assessment.category,
        gradingMode=assessment.grading_mode,
        scoringPolicy=assessment.scoring_policy,
        questions=[question_to_dto(q) for q in assessment.questions.all()],
        questionGroups=groups,
    )


def question_to_dto(question: Question) -> QuestionDTO:
    """Convert a Question to a DTO.

    Expects question.mcq_choices, question.multiple_choice, question.short_answer,
    and question.number_scale to be prefetched by the caller for optimal performance.
    """
    data: dict | None = None
    select_all = None
    min_value = None
    max_value = None
    try:
        if question.kind == QuestionKind.MULTIPLE_CHOICE:
            choices = [
                {"prompt": choice.choice_text, "score": choice.points}
                for choice in question.mcq_choices.all()
            ]
            select_all = question.multiple_choice.select_all
            data = {"choices": choices, "selectAll": select_all, "correctAnswers": []}
        elif question.kind == QuestionKind.SHORT_ANSWER:
            data = {
                "caseSensitive": question.short_answer.case_sensitive,
                "trim": question.short_answer.trim,
            }
        elif question.kind == QuestionKind.NUMBER_SCALE:
            min_value = question.number_scale.min
            max_value = question.number_scale.max
            data = {
                "min": min_value,
                "max": max_value,
                "target": question.number_scale.target,
            }
    except ObjectDoesNotExist:
        pass

    return QuestionDTO(
        questionId=question.id,
        id=question.id,
        type=question.kind,
        prompt=question.prompt,
        maxPoints=question.max_points,
        autoGradable=question.auto_gradable,
        graded=question.graded,
        selectAll=select_all,
        min=min_value,
        max=max_value,
        data=data,
        groupId=question.question_group_id,
        rubricId=question.rubric_id,
        gradingStrategy=question.grading_strategy,
    )


@transaction.atomic
def create_assessment(request_user: User, payload: dict) -> Assessment:
    grading_mode = payload.get("gradingMode")
    scoring_policy = payload.get("scoringPolicy", ScoringPolicy.STANDARD)
    title = payload.get("title")
    if not grading_mode:
        raise ValueError("gradingMode is required")
    if not title:
        raise ValueError("title is required")

    questions_payload = payload.get("questions") or []

    assessment = Assessment.objects.create(
        title=title,
        grading_mode=grading_mode,
        scoring_policy=scoring_policy,
        created_by_admin=request_user,
        category=payload.get("category"),
    )
    group_map = _create_question_groups(assessment, payload.get("questionGroups") or [])
    _replace_questions(assessment, questions_payload, group_map)
    _validate_rubric_rules(assessment)
    return assessment



@transaction.atomic
def update_assessment(assessment: Assessment, payload: dict) -> Assessment:
    if Assignment.objects.filter(assessment=assessment).exists():
        raise AssessmentReferencedError("Cannot update assessment referenced by assignments")

    grading_mode = payload.get("gradingMode", assessment.grading_mode)
    scoring_policy = payload.get("scoringPolicy", assessment.scoring_policy)
    questions_payload = payload.get("questions") or []

    assessment.title = payload.get("title", assessment.title)
    assessment.category = payload.get("category")
    assessment.grading_mode = grading_mode
    assessment.scoring_policy = scoring_policy
    assessment.save()

    # Replace question groups
    AssessmentQuestionGroup.objects.filter(assessment=assessment).delete()
    group_map = _create_question_groups(assessment, payload.get("questionGroups") or [])
    _replace_questions(assessment, questions_payload, group_map)
    _validate_rubric_rules(assessment)
    return assessment


@transaction.atomic
def delete_assessment(assessment: Assessment) -> None:
    if Assignment.objects.filter(assessment=assessment).exists():
        raise AssessmentReferencedError("Cannot delete assessment referenced by assignments")
    assessment.delete()


def list_assessments(include_archived: bool = False) -> list[Assessment]:
    """List assessments with related data prefetched for DTO conversion.

    By default only ACTIVE; set include_archived=True for all.
    """
    qs = Assessment.objects.all()
    if not include_archived:
        qs = qs.filter(status=AssessmentStatus.ACTIVE)
    return list(
        qs.prefetch_related(
            "question_groups",
            "questions__mcq_choices",
            "questions__multiple_choice",
            "questions__short_answer",
            "questions__number_scale",
        )
    )


@transaction.atomic
def archive_assessment(request_user: User, assessment: Assessment) -> Assessment:
    """ARCH-UC-01: Archive an assessment template."""
    if assessment.status == AssessmentStatus.ARCHIVED:
        raise ConflictError("Assessment is already archived.")
    assessment.status = AssessmentStatus.ARCHIVED
    assessment.archived_at = timezone.now()
    assessment.archived_by = request_user
    assessment.save(update_fields=["status", "archived_at", "archived_by"])
    return assessment


@transaction.atomic
def restore_assessment(request_user: User, assessment: Assessment) -> Assessment:
    """ARCH-UC-04: Restore an archived assessment."""
    if assessment.status != AssessmentStatus.ARCHIVED:
        raise ConflictError("Assessment is not archived.")
    assessment.status = AssessmentStatus.ACTIVE
    assessment.archived_at = None
    assessment.archived_by = None
    assessment.restored_at = timezone.now()
    assessment.restored_by = request_user
    assessment.save(update_fields=["status", "archived_at", "archived_by", "restored_at", "restored_by"])
    return assessment


@transaction.atomic
def purge_assessment(assessment: Assessment) -> None:
    """ARCH-UC-06: Hard-delete an archived assessment. Admin-only."""
    if assessment.status != AssessmentStatus.ARCHIVED:
        raise ConflictError("Only archived assessments can be purged.")
    if Assignment.objects.filter(assessment=assessment).exists():
        raise ConflictError("Cannot purge: assessment has associated assignments.")
    assessment.delete()


def _create_question_groups(
    assessment: Assessment, groups: list[dict]
) -> dict[str, AssessmentQuestionGroup]:
    """Create question groups and return a map from clientKey to model instance."""
    from rubrics.models import Rubric, RubricStatus

    group_map: dict[str, AssessmentQuestionGroup] = {}
    for idx, g in enumerate(groups):
        rubric_id = g.get("rubricId")
        if rubric_id:
            rubric = Rubric.objects.filter(id=rubric_id).first()
            if not rubric:
                raise ValueError(f"Rubric {rubric_id} not found")
            if rubric.status == RubricStatus.ARCHIVED:
                raise ValueError(f"Cannot attach archived rubric {rubric_id}")
        group = AssessmentQuestionGroup.objects.create(
            assessment=assessment,
            name=g.get("name", f"Group {idx + 1}"),
            rubric_id=rubric_id,
            order_index=g.get("orderIndex", idx),
        )
        client_key = g.get("clientKey", str(idx))
        group_map[client_key] = group
    return group_map


def _replace_questions(
    assessment: Assessment,
    questions: Iterable[dict],
    group_map: dict[str, AssessmentQuestionGroup] | None = None,
) -> None:
    Question.objects.filter(assessment=assessment).delete()
    for question_payload in questions:
        _create_question(assessment, question_payload, group_map or {})


def _create_question(
    assessment: Assessment,
    payload: dict,
    group_map: dict[str, AssessmentQuestionGroup],
) -> Question:
    from rubrics.models import Rubric, RubricStatus

    kind = payload.get("type")
    if not kind:
        raise ValueError("Question type is required")
    prompt = payload.get("prompt")
    if not prompt:
        raise ValueError("Question prompt is required")

    # Resolve question group
    group_key = payload.get("groupClientKey")
    question_group = group_map.get(group_key) if group_key else None

    # Resolve per-question rubric
    rubric_id = payload.get("rubricId")
    if rubric_id:
        rubric = Rubric.objects.filter(id=rubric_id).first()
        if not rubric:
            raise ValueError(f"Rubric {rubric_id} not found")
        if rubric.status == RubricStatus.ARCHIVED:
            raise ValueError(f"Cannot attach archived rubric {rubric_id}")

    grading_strategy = payload.get("gradingStrategy", GradingStrategy.AUTO)

    question = Question.objects.create(
        assessment=assessment,
        question_type=kind,
        kind=kind,
        prompt=prompt,
        max_points=payload.get("maxPoints") or 0,
        auto_gradable=kind in (QuestionKind.MULTIPLE_CHOICE, QuestionKind.NUMBER_SCALE),
        graded=False,
        question_group=question_group,
        rubric_id=rubric_id,
        grading_strategy=grading_strategy,
    )
    data = payload.get("data") or {}

    if kind == QuestionKind.MULTIPLE_CHOICE:
        MultipleChoiceQuestion.objects.create(
            question=question, select_all=data.get("selectAll") or False
        )
        for choice in data.get("choices", []):
            McqChoice.objects.create(
                question=question,
                choice_text=choice.get("prompt"),
                points=choice.get("score") or 0,
            )
    elif kind == QuestionKind.SHORT_ANSWER:
        ShortAnswerQuestion.objects.create(
            question=question,
            case_sensitive=bool(data.get("caseSensitive")),
            trim=bool(data.get("trim", True)),
        )
    elif kind == QuestionKind.NUMBER_SCALE:
        min_value = data.get("min")
        max_value = data.get("max")
        if min_value is None or max_value is None:
            raise ValueError("min and max are required for number scale questions")
        if min_value is not None and max_value is not None and min_value > max_value:
            min_value, max_value = max_value, min_value
        NumberScaleQuestion.objects.create(
            question=question,
            min=min_value,
            max=max_value,
            target=data.get("target"),
        )
    return question


def _validate_rubric_rules(assessment: Assessment) -> None:
    """Validate rubric linkage rules based on grading mode."""
    mode = assessment.grading_mode
    questions = assessment.questions.all()

    for q in questions:
        has_rubric = q.rubric_id is not None or (
            q.question_group and q.question_group.rubric_id is not None
        )
        strategy = q.grading_strategy

        if mode == GradingMode.AUTO:
            if has_rubric:
                raise ValueError("AUTO mode does not allow rubric linkage")
        elif mode == GradingMode.MANUAL:
            if not has_rubric:
                raise ValueError(
                    f"MANUAL question '{q.prompt[:30]}' must have a rubric"
                )
        elif mode == GradingMode.HYBRID:
            if strategy == GradingStrategy.MANUAL and not has_rubric:
                raise ValueError(
                    f"HYBRID question '{q.prompt[:30]}' with MANUAL strategy must have a rubric"
                )
            if strategy == GradingStrategy.AUTO and has_rubric:
                raise ValueError(
                    f"HYBRID question '{q.prompt[:30]}' with AUTO strategy must not have a rubric"
                )
