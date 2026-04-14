"""Assignment template domain helpers."""

from collections.abc import Iterable

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from accounts.models import User
from assignments.models import Assignment
from core.dtos import AssignmentTemplateDTO, QuestionDTO, QuestionGroupDTO, QuestionImageDTO
from core.lifecycle import ConflictError

from .models import (
    AssignmentTemplate,
    AssignmentTemplateQuestionGroup,
    AssignmentTemplateStatus,
    GradingMode,
    GradingStrategy,
    McqChoice,
    MultipleChoiceQuestion,
    NumberScaleQuestion,
    Question,
    QuestionKind,
    ScoringPolicy,
    ShortAnswerQuestion,
    SubmissionMode,
)


class AssignmentTemplateReferencedError(Exception):
    """Raised when assignments already reference an assignment template."""


def _assignment_template_with_related(assignment_template_id: int) -> AssignmentTemplate | None:
    """Fetch an assignment template with related questions prefetched."""
    return (
        AssignmentTemplate.objects.filter(id=assignment_template_id)
        .prefetch_related(
            Prefetch(
                "question_groups",
                queryset=AssignmentTemplateQuestionGroup.objects.order_by("order_index"),
            ),
            "questions__mcq_choices",
            "questions__multiple_choice",
            "questions__short_answer",
            "questions__number_scale",
        )
        .first()
    )


def assignment_template_to_dto(
    assignment_template: AssignmentTemplate,
) -> AssignmentTemplateDTO:
    """Convert an assignment template to a DTO."""
    groups = [
        QuestionGroupDTO(
            id=group.id,
            name=group.name,
            rubricId=group.rubric_id,
            orderIndex=group.order_index,
        )
        for group in assignment_template.question_groups.all()
    ]
    return AssignmentTemplateDTO(
        id=assignment_template.id,
        title=assignment_template.title,
        category=assignment_template.category,
        gradingMode=assignment_template.grading_mode,
        scoringPolicy=assignment_template.scoring_policy,
        submissionMode=assignment_template.submission_mode,
        status=assignment_template.status,
        rubricId=assignment_template.rubric_id,
        questions=[question_to_dto(question) for question in assignment_template.questions.all()],
        questionGroups=groups,
    )


def question_to_dto(question: Question) -> QuestionDTO:
    """Convert a question and its subtype data to a DTO."""
    from .image_services import question_image_to_dto

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

    image_payload = question_image_to_dto(question)
    image_dto = QuestionImageDTO(**image_payload) if image_payload else None

    return QuestionDTO(
        questionId=question.id,
        id=question.id,
        type=question.kind,
        prompt=question.prompt,
        maxPoints=question.max_points,
        autoGradable=question.auto_gradable,
        graded=question.graded,
        image=image_dto,
        selectAll=select_all,
        min=min_value,
        max=max_value,
        data=data,
        groupId=question.question_group_id,
        rubricId=question.rubric_id,
        gradingStrategy=question.grading_strategy,
    )


@transaction.atomic
def create_assignment_template_draft(request_user: User) -> AssignmentTemplate:
    """Create an empty draft assignment template with a placeholder question."""
    assignment_template = AssignmentTemplate.objects.create(
        title="",
        grading_mode=GradingMode.AUTO,
        scoring_policy=ScoringPolicy.STANDARD,
        submission_mode=SubmissionMode.DIGITAL,
        created_by_admin=request_user,
        status=AssignmentTemplateStatus.DRAFT,
    )
    Question.objects.create(
        assignment_template=assignment_template,
        question_type=QuestionKind.MULTIPLE_CHOICE,
        kind=QuestionKind.MULTIPLE_CHOICE,
        prompt="",
        max_points=0,
        auto_gradable=True,
        graded=False,
        grading_strategy=GradingStrategy.AUTO,
    )
    return assignment_template


@transaction.atomic
def create_assignment_template(request_user: User, payload: dict) -> AssignmentTemplate:
    """Create an assignment template from a validated payload."""
    grading_mode = payload.get("gradingMode")
    scoring_policy = payload.get("scoringPolicy", ScoringPolicy.STANDARD)
    submission_mode = payload.get("submissionMode", SubmissionMode.DIGITAL)
    title = payload.get("title")
    if not grading_mode:
        raise ValueError("gradingMode is required")
    if not title:
        raise ValueError("title is required")

    if submission_mode in (SubmissionMode.UPLOAD_ONLY, SubmissionMode.DIGITAL_WITH_UPLOAD):
        grading_mode = GradingMode.MANUAL

    questions_payload = payload.get("questions") or []
    template_rubric_id = _resolve_assignment_template_rubric_id(payload.get("rubricId"))

    assignment_template = AssignmentTemplate.objects.create(
        title=title,
        grading_mode=grading_mode,
        scoring_policy=scoring_policy,
        submission_mode=submission_mode,
        created_by_admin=request_user,
        category=payload.get("category"),
        rubric_id=template_rubric_id,
    )
    group_map = _create_question_groups(
        assignment_template,
        payload.get("questionGroups") or [],
    )
    _replace_questions(assignment_template, questions_payload, group_map)
    _validate_rubric_rules(assignment_template)
    return assignment_template


@transaction.atomic
def update_assignment_template(
    assignment_template: AssignmentTemplate,
    payload: dict,
) -> AssignmentTemplate:
    """Update an assignment template when it is not already assigned."""
    if Assignment.objects.filter(assignment_template=assignment_template).exists():
        raise AssignmentTemplateReferencedError(
            "Cannot update assignment template referenced by assignments"
        )

    grading_mode = payload.get("gradingMode", assignment_template.grading_mode)
    scoring_policy = payload.get("scoringPolicy", assignment_template.scoring_policy)
    submission_mode = payload.get("submissionMode", assignment_template.submission_mode)
    questions_payload = payload.get("questions") or []
    template_rubric_id = _resolve_assignment_template_rubric_id(
        payload.get("rubricId", assignment_template.rubric_id)
    )

    if submission_mode in (SubmissionMode.UPLOAD_ONLY, SubmissionMode.DIGITAL_WITH_UPLOAD):
        grading_mode = GradingMode.MANUAL

    assignment_template.title = payload.get("title", assignment_template.title)
    assignment_template.category = payload.get("category")
    assignment_template.grading_mode = grading_mode
    assignment_template.scoring_policy = scoring_policy
    assignment_template.submission_mode = submission_mode
    assignment_template.rubric_id = template_rubric_id
    assignment_template.save()

    AssignmentTemplateQuestionGroup.objects.filter(
        assignment_template=assignment_template
    ).delete()
    group_map = _create_question_groups(
        assignment_template,
        payload.get("questionGroups") or [],
    )
    _replace_questions(
        assignment_template,
        questions_payload,
        group_map,
        allow_incomplete=assignment_template.status == AssignmentTemplateStatus.DRAFT,
    )

    if assignment_template.status != AssignmentTemplateStatus.DRAFT:
        _validate_rubric_rules(assignment_template)

    return assignment_template


@transaction.atomic
def publish_assignment_template(assignment_template: AssignmentTemplate) -> AssignmentTemplate:
    """Transition a draft assignment template to active."""
    if assignment_template.status != AssignmentTemplateStatus.DRAFT:
        raise ConflictError("Only draft assignment templates can be published.")

    if not assignment_template.title.strip():
        raise ValueError("Assignment template title is required before publishing.")

    questions = list(assignment_template.questions.all())
    if not questions and assignment_template.submission_mode != SubmissionMode.UPLOAD_ONLY:
        raise ValueError("Assignment template must have at least one question.")

    for question in questions:
        if not question.prompt.strip():
            raise ValueError(f"Question '{question.kind}' is missing prompt text.")

    if questions:
        _validate_rubric_rules(assignment_template)

    assignment_template.status = AssignmentTemplateStatus.ACTIVE
    assignment_template.save(update_fields=["status"])
    return assignment_template


@transaction.atomic
def delete_assignment_template_draft(assignment_template: AssignmentTemplate) -> None:
    """Hard-delete a draft assignment template."""
    if assignment_template.status != AssignmentTemplateStatus.DRAFT:
        raise ConflictError("Only draft assignment templates can be deleted.")
    assignment_template.delete()


@transaction.atomic
def delete_assignment_template(assignment_template: AssignmentTemplate) -> None:
    """Delete an assignment template that is not referenced by assignments."""
    if Assignment.objects.filter(assignment_template=assignment_template).exists():
        raise AssignmentTemplateReferencedError(
            "Cannot delete assignment template referenced by assignments"
        )
    assignment_template.delete()


def list_assignment_templates(
    include_archived: bool = False,
    include_drafts: bool = False,
) -> list[AssignmentTemplate]:
    """List assignment templates with related data prefetched."""
    queryset = AssignmentTemplate.objects.all()
    if not include_archived and not include_drafts:
        queryset = queryset.filter(status=AssignmentTemplateStatus.ACTIVE)
    elif include_drafts and not include_archived:
        queryset = queryset.filter(
            status__in=[AssignmentTemplateStatus.ACTIVE, AssignmentTemplateStatus.DRAFT]
        )
    elif include_archived and not include_drafts:
        queryset = queryset.filter(
            status__in=[AssignmentTemplateStatus.ACTIVE, AssignmentTemplateStatus.ARCHIVED]
        )

    return list(
        queryset.prefetch_related(
            Prefetch(
                "question_groups",
                queryset=AssignmentTemplateQuestionGroup.objects.order_by("order_index"),
            ),
            "questions__mcq_choices",
            "questions__multiple_choice",
            "questions__short_answer",
            "questions__number_scale",
        )
    )


@transaction.atomic
def archive_assignment_template(
    request_user: User,
    assignment_template: AssignmentTemplate,
) -> AssignmentTemplate:
    """Archive an assignment template."""
    if assignment_template.status == AssignmentTemplateStatus.ARCHIVED:
        raise ConflictError("Assignment template is already archived.")
    assignment_template.status = AssignmentTemplateStatus.ARCHIVED
    assignment_template.archived_at = timezone.now()
    assignment_template.archived_by = request_user
    assignment_template.save(update_fields=["status", "archived_at", "archived_by"])
    return assignment_template


@transaction.atomic
def restore_assignment_template(
    request_user: User,
    assignment_template: AssignmentTemplate,
) -> AssignmentTemplate:
    """Restore an archived assignment template."""
    if assignment_template.status != AssignmentTemplateStatus.ARCHIVED:
        raise ConflictError("Assignment template is not archived.")
    assignment_template.status = AssignmentTemplateStatus.ACTIVE
    assignment_template.archived_at = None
    assignment_template.archived_by = None
    assignment_template.restored_at = timezone.now()
    assignment_template.restored_by = request_user
    assignment_template.save(
        update_fields=["status", "archived_at", "archived_by", "restored_at", "restored_by"]
    )
    return assignment_template


@transaction.atomic
def purge_assignment_template(assignment_template: AssignmentTemplate) -> None:
    """Hard-delete an archived assignment template."""
    if assignment_template.status != AssignmentTemplateStatus.ARCHIVED:
        raise ConflictError("Only archived assignment templates can be purged.")
    if Assignment.objects.filter(assignment_template=assignment_template).exists():
        raise ConflictError("Cannot purge: assignment template has associated assignments.")
    assignment_template.delete()


def _create_question_groups(
    assignment_template: AssignmentTemplate,
    groups: list[dict],
) -> dict[str, AssignmentTemplateQuestionGroup]:
    """Create question groups and return a clientKey -> instance map."""
    from rubrics.models import Rubric, RubricStatus

    group_map: dict[str, AssignmentTemplateQuestionGroup] = {}
    for index, group_payload in enumerate(groups):
        rubric_id = group_payload.get("rubricId")
        if rubric_id:
            rubric = Rubric.objects.filter(id=rubric_id).first()
            if not rubric:
                raise ValueError(f"Rubric {rubric_id} not found")
            if rubric.status == RubricStatus.ARCHIVED:
                raise ValueError(f"Cannot attach archived rubric {rubric_id}")
        group = AssignmentTemplateQuestionGroup.objects.create(
            assignment_template=assignment_template,
            name=group_payload.get("name", f"Group {index + 1}"),
            rubric_id=rubric_id,
            order_index=group_payload.get("orderIndex", index),
        )
        client_key = group_payload.get("clientKey", str(index))
        group_map[client_key] = group
    return group_map


def _resolve_assignment_template_rubric_id(rubric_id: int | None) -> int | None:
    """Validate a top-level assignment template rubric reference."""
    from rubrics.models import Rubric, RubricStatus

    if rubric_id is None:
        return None

    rubric = Rubric.objects.filter(id=rubric_id).first()
    if not rubric:
        raise ValueError(f"Rubric {rubric_id} not found")
    if rubric.status == RubricStatus.ARCHIVED:
        raise ValueError(f"Cannot attach archived rubric {rubric_id}")
    return rubric.id


def _replace_questions(
    assignment_template: AssignmentTemplate,
    questions: Iterable[dict],
    group_map: dict[str, AssignmentTemplateQuestionGroup] | None = None,
    allow_incomplete: bool = False,
) -> None:
    """Replace all questions for an assignment template."""
    Question.objects.filter(assignment_template=assignment_template).delete()
    for question_payload in questions:
        _create_question(
            assignment_template,
            question_payload,
            group_map or {},
            allow_incomplete=allow_incomplete,
        )


def _derive_question_max_points(kind: str, data: dict, fallback: float | int | None) -> float:
    """Compute question max points from payload data when applicable."""
    if kind == QuestionKind.MULTIPLE_CHOICE:
        positive_scores = [
            float(choice.get("score") or 0)
            for choice in data.get("choices", [])
            if (choice.get("score") or 0) > 0
        ]
        if not positive_scores:
            return 0.0
        if data.get("selectAll"):
            return float(sum(positive_scores))
        return float(max(positive_scores))

    return float(fallback or 0)


def _create_question(
    assignment_template: AssignmentTemplate,
    payload: dict,
    group_map: dict[str, AssignmentTemplateQuestionGroup],
    allow_incomplete: bool = False,
) -> Question:
    """Create a question and subtype rows for an assignment template."""
    from rubrics.models import Rubric, RubricStatus

    kind = payload.get("type")
    if not kind:
        raise ValueError("Question type is required")

    prompt = payload.get("prompt", "")
    if not prompt and not allow_incomplete:
        raise ValueError("Question prompt is required")

    group_key = payload.get("groupClientKey")
    question_group = group_map.get(group_key) if group_key else None

    rubric_id = payload.get("rubricId")
    if rubric_id:
        rubric = Rubric.objects.filter(id=rubric_id).first()
        if not rubric:
            raise ValueError(f"Rubric {rubric_id} not found")
        if rubric.status == RubricStatus.ARCHIVED:
            raise ValueError(f"Cannot attach archived rubric {rubric_id}")

    grading_strategy = payload.get("gradingStrategy", GradingStrategy.AUTO)
    image_json = payload.get("image")
    data = payload.get("data") or {}
    max_points = _derive_question_max_points(kind, data, payload.get("maxPoints"))

    question = Question.objects.create(
        assignment_template=assignment_template,
        question_type=kind,
        kind=kind,
        prompt=prompt,
        max_points=max_points,
        auto_gradable=kind in (QuestionKind.MULTIPLE_CHOICE, QuestionKind.NUMBER_SCALE),
        graded=False,
        image=image_json if isinstance(image_json, str) else None,
        question_group=question_group,
        rubric_id=rubric_id,
        grading_strategy=grading_strategy,
    )

    if kind == QuestionKind.MULTIPLE_CHOICE:
        MultipleChoiceQuestion.objects.create(
            question=question,
            select_all=data.get("selectAll") or False,
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
        if (min_value is None or max_value is None) and not allow_incomplete:
            raise ValueError("min and max are required for number scale questions")
        if allow_incomplete and min_value is None:
            min_value = 1
        if allow_incomplete and max_value is None:
            max_value = 5
        if min_value is not None and max_value is not None and min_value > max_value:
            min_value, max_value = max_value, min_value
        NumberScaleQuestion.objects.create(
            question=question,
            min=min_value,
            max=max_value,
            target=data.get("target"),
        )

    return question


def _validate_rubric_rules(assignment_template: AssignmentTemplate) -> None:
    """Validate rubric linkage rules based on grading mode."""
    mode = assignment_template.grading_mode
    questions = list(assignment_template.questions.all())
    has_template_rubric = assignment_template.rubric_id is not None
    has_specific_rubrics = any(
        question.rubric_id is not None
        or (question.question_group and question.question_group.rubric_id is not None)
        for question in questions
    )

    if has_template_rubric and has_specific_rubrics:
        raise ValueError(
            "Assignment template rubric cannot be combined with question or group rubrics"
        )

    for question in questions:
        has_rubric = (
            question.rubric_id is not None
            or (question.question_group and question.question_group.rubric_id is not None)
            or assignment_template.rubric_id is not None
        )
        strategy = question.grading_strategy

        if mode == GradingMode.AUTO:
            if has_rubric:
                raise ValueError("AUTO mode does not allow rubric linkage")
        elif mode == GradingMode.MANUAL:
            if not has_rubric:
                raise ValueError(
                    f"MANUAL question '{question.prompt[:30]}' must have a rubric"
                )
        elif mode == GradingMode.HYBRID:
            if strategy == GradingStrategy.MANUAL and not has_rubric:
                raise ValueError(
                    f"HYBRID question '{question.prompt[:30]}' with MANUAL strategy must have a rubric"
                )
            if strategy == GradingStrategy.AUTO and has_rubric:
                raise ValueError(
                    f"HYBRID question '{question.prompt[:30]}' with AUTO strategy must not have a rubric"
                )
