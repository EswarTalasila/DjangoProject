"""Assignment-owned content snapshots and teacher extension helpers."""

from __future__ import annotations

import json
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Max, Prefetch

from assignment_templates.models import (
    AssignmentTemplate,
    AssignmentTemplateQuestionGroup,
    Question,
    QuestionKind,
)
from assignment_templates.services import question_to_dto
from core.dtos import (
    AssignmentContentDTO,
    QuestionDTO,
    QuestionGroupDTO,
    QuestionImageDTO,
    TeacherCriterionDTO,
    TeacherCriterionLevelDTO,
)
from core.helpers import answer_type_from_question
from submissions.models import (
    Answer,
    MultipleChoiceAnswer,
    MultipleChoiceSelected,
    NumberScaleAnswer,
    ShortAnswerAnswer,
    Submission,
    SubmissionStatus,
)

from ..models import (
    Assignment,
    AssignmentContentOrigin,
    AssignmentQuestion,
    AssignmentQuestionGroup,
    AssignmentTeacherCriterion,
    AssignmentTeacherCriterionLevel,
)


def _content_queryset():
    """Return the eager-loading queryset used for assignment content reads."""
    return Assignment.objects.select_related("assignment_template").prefetch_related(
        Prefetch(
            "question_groups",
            queryset=AssignmentQuestionGroup.objects.order_by("order_index", "id"),
        ),
        Prefetch(
            "questions",
            queryset=AssignmentQuestion.objects.select_related("question_group").order_by(
                "order_index", "id"
            ),
        ),
        Prefetch(
            "teacher_criteria",
            queryset=AssignmentTeacherCriterion.objects.prefetch_related(
                Prefetch(
                    "levels",
                    queryset=AssignmentTeacherCriterionLevel.objects.order_by("order_index", "id"),
                )
            ).order_by("order_index", "id"),
        ),
    )


def _assert_can_compose(assignment: Assignment, caller_user) -> None:
    """Enforce the shared mutability rules for teacher-managed assignment additions."""
    if assignment.created_by_id != caller_user.id and not caller_user.is_staff:
        raise PermissionError("Only the assignment owner or an admin can extend this assignment.")
    if assignment.status == "ARCHIVED":
        raise ValueError("Archived assignments cannot be extended.")
    if assignment_has_progressed_submissions(assignment):
        raise ValueError("Cannot extend an assignment after submissions have started.")


def _create_answer_shell(submission: Submission, question: AssignmentQuestion) -> Answer:
    """Create the placeholder answer and subtype row for a submission/question pair."""
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
    return answer


def provision_submission_answers(submission: Submission) -> None:
    """Ensure a submission has placeholder answers for every assignment-owned question."""
    assignment = submission.assignment
    if not assignment.questions.exists():
        snapshot_assignment_content(
            assignment,
            assignment.assignment_template,
            creator_user_id=assignment.created_by_id,
        )
    existing_question_ids = set(
        Answer.objects.filter(submission=submission).values_list("question_id", flat=True)
    )
    for question in assignment.questions.order_by("order_index", "id"):
        if question.id in existing_question_ids:
            continue
        _create_answer_shell(submission, question)


def get_assignment_with_content(assignment_id: int) -> Assignment | None:
    """Fetch an assignment with its snapshot content eagerly loaded.

    Older assignments may predate assignment-owned snapshots because they were
    created before the extension model landed or were inserted directly in tests.
    We backfill the snapshot the first time those assignments are loaded so the
    rest of the system can treat assignment content as canonical.
    """
    assignment = Assignment.objects.select_related("assignment_template").filter(id=assignment_id).first()
    if not assignment:
        return None
    if not AssignmentQuestion.objects.filter(assignment=assignment).exists():
        snapshot_assignment_content(
            assignment,
            assignment.assignment_template,
            creator_user_id=assignment.created_by_id,
        )
    return _content_queryset().filter(id=assignment_id).first()


def _parse_image_meta(image_value: str | None) -> dict[str, Any] | None:
    """Parse stored image JSON metadata into a dict."""
    if not image_value:
        return None
    try:
        payload = json.loads(image_value)
    except (TypeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def assignment_question_to_dto(question: AssignmentQuestion) -> QuestionDTO:
    """Convert an assignment-owned question snapshot to a DTO."""
    image_payload = _parse_image_meta(question.image)
    image_dto = None
    if image_payload:
        image_dto = QuestionImageDTO(
            id=image_payload.get("assetId", ""),
            storageKey=image_payload.get("storageKey", ""),
            url=f"/api/v1/assignments/images/{image_payload.get('storageKey', '')}",
            originalFilename=image_payload.get("originalFilename", ""),
            mimeType=image_payload.get("mimeType", ""),
            sizeBytes=image_payload.get("sizeBytes", 0),
        )

    data = question.data if isinstance(question.data, dict) else None
    return QuestionDTO(
        questionId=question.id,
        id=question.id,
        type=question.kind,
        prompt=question.prompt,
        maxPoints=question.max_points,
        autoGradable=question.auto_gradable,
        graded=question.graded,
        image=image_dto,
        data=data,
        selectAll=(data or {}).get("selectAll"),
        min=(data or {}).get("min"),
        max=(data or {}).get("max"),
        groupId=question.question_group_id,
        rubricId=None,
        gradingStrategy=question.grading_strategy,
        orderIndex=question.order_index,
        origin=question.origin,
        lockedFromSource=question.locked_from_source,
        sourceQuestionId=question.source_template_question_id,
    )


def assignment_content_to_dto(assignment: Assignment) -> AssignmentContentDTO:
    """Build the effective assignment-content DTO from assignment-owned snapshots."""
    assignment_template = assignment.assignment_template
    groups = [
        QuestionGroupDTO(
            id=group.id,
            name=group.name,
            rubricId=None,
            orderIndex=group.order_index,
        )
        for group in assignment.question_groups.all()
    ]
    teacher_criteria = [
        TeacherCriterionDTO(
            id=criterion.id,
            title=criterion.title,
            description=criterion.description,
            weight=criterion.weight,
            orderIndex=criterion.order_index,
            levels=[
                TeacherCriterionLevelDTO(
                    id=level.id,
                    label=level.label,
                    points=level.points,
                    description=level.description,
                    orderIndex=level.order_index,
                )
                for level in criterion.levels.all()
            ],
        )
        for criterion in assignment.teacher_criteria.all()
    ]
    return AssignmentContentDTO(
        id=assignment.assignment_template_id,
        title=assignment_template.title,
        assignmentId=assignment.id,
        assignmentTemplateId=assignment.assignment_template_id,
        assignmentTemplateTitle=assignment_template.title,
        category=assignment_template.category,
        gradingMode=assignment_template.grading_mode,
        scoringPolicy=assignment_template.scoring_policy,
        submissionMode=assignment_template.submission_mode,
        rubricId=assignment_template.rubric_id,
        questions=[assignment_question_to_dto(question) for question in assignment.questions.all()],
        questionGroups=groups,
        teacherCriteria=teacher_criteria,
    )


@transaction.atomic
def snapshot_assignment_content(
    assignment: Assignment,
    assignment_template: AssignmentTemplate,
    *,
    creator_user_id: int | None = None,
) -> None:
    """Copy the current template question/group graph into assignment-owned snapshots."""
    if assignment.questions.exists():
        return

    group_map: dict[int, AssignmentQuestionGroup] = {}
    template_groups = AssignmentTemplateQuestionGroup.objects.filter(
        assignment_template=assignment_template
    ).order_by("order_index", "id")
    for template_group in template_groups:
        group_map[template_group.id] = AssignmentQuestionGroup.objects.create(
            assignment=assignment,
            source_template_group=template_group,
            name=template_group.name,
            order_index=template_group.order_index,
            origin=AssignmentContentOrigin.TEMPLATE,
            locked_from_source=True,
        )

    template_questions = Question.objects.filter(assignment_template=assignment_template).order_by("id")
    created_questions: list[AssignmentQuestion] = []
    for order_index, template_question in enumerate(template_questions):
        dto = question_to_dto(template_question)
        created_questions.append(
            AssignmentQuestion.objects.create(
            assignment=assignment,
            source_template_question=template_question,
            question_group=group_map.get(template_question.question_group_id),
            created_by_id=creator_user_id,
            kind=template_question.kind,
            prompt=template_question.prompt,
            max_points=template_question.max_points,
            auto_gradable=template_question.auto_gradable,
            graded=template_question.graded,
            image=template_question.image,
            grading_strategy=template_question.grading_strategy,
            data=dto.data or {},
            order_index=order_index,
            origin=AssignmentContentOrigin.TEMPLATE,
            locked_from_source=True,
            )
        )

    # Backfill placeholder answers for legacy submissions when the snapshot is
    # created after the assignment already exists.
    if created_questions:
        for submission in assignment.submissions.all():
            provision_submission_answers(submission)


def assignment_has_progressed_submissions(assignment: Assignment) -> bool:
    """Return True when any submission has moved past NOT_STARTED."""
    return assignment.submissions.exclude(status=SubmissionStatus.NOT_STARTED).exists()


def _next_question_order(assignment: Assignment) -> int:
    """Return the next order index for assignment-local questions."""
    return int(assignment.questions.aggregate(value=Max("order_index")).get("value") or 0) + 1


def _next_teacher_criterion_order(assignment: Assignment) -> int:
    """Return the next order index for assignment-local teacher criteria."""
    return int(assignment.teacher_criteria.aggregate(value=Max("order_index")).get("value") or 0) + 1


def _next_teacher_criterion_level_order(criterion: AssignmentTeacherCriterion) -> int:
    """Return the next order index for teacher-authored levels on a criterion."""
    return int(criterion.levels.aggregate(value=Max("order_index")).get("value") or 0) + 1


def _get_teacher_criterion(assignment: Assignment, criterion_id: int) -> AssignmentTeacherCriterion:
    """Resolve a teacher-authored criterion for the assignment or fail with ValueError."""
    criterion = (
        AssignmentTeacherCriterion.objects.prefetch_related("levels")
        .filter(id=criterion_id, assignment=assignment)
        .first()
    )
    if not criterion:
        raise ValueError("Teacher criterion not found.")
    return criterion


@transaction.atomic
def add_assignment_question(assignment: Assignment, caller_user, payload: dict) -> AssignmentQuestion:
    """Create a teacher-owned assignment-local question and provision it onto existing submissions."""
    _assert_can_compose(assignment, caller_user)

    kind = payload.get("type")
    prompt = (payload.get("prompt") or "").strip()
    if not kind:
        raise ValueError("type is required")
    if not prompt:
        raise ValueError("prompt is required")
    max_points = payload.get("maxPoints")
    if max_points is None:
        raise ValueError("maxPoints is required")

    question = AssignmentQuestion.objects.create(
        assignment=assignment,
        created_by=caller_user,
        kind=kind,
        prompt=prompt,
        max_points=max_points,
        auto_gradable=bool(payload.get("autoGradable", kind != "SHORT_ANSWER")),
        graded=bool(payload.get("graded", False)),
        grading_strategy=payload.get("gradingStrategy", "AUTO"),
        data=payload.get("data") or {},
        order_index=_next_question_order(assignment),
        origin=AssignmentContentOrigin.TEACHER_ADDITION,
        locked_from_source=False,
    )
    for submission in assignment.submissions.all():
        _create_answer_shell(submission, question)
    return question


@transaction.atomic
def add_assignment_teacher_criterion(
    assignment: Assignment,
    caller_user,
    payload: dict,
) -> AssignmentTeacherCriterion:
    """Create a teacher-authored assignment-local criterion."""
    _assert_can_compose(assignment, caller_user)

    title = (payload.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")
    weight = payload.get("weight")
    if weight is None:
        raise ValueError("weight is required")

    return AssignmentTeacherCriterion.objects.create(
        assignment=assignment,
        created_by=caller_user,
        title=title,
        description=(payload.get("description") or "").strip(),
        weight=weight,
        order_index=_next_teacher_criterion_order(assignment),
    )


@transaction.atomic
def reorder_assignment_questions(
    assignment: Assignment,
    caller_user,
    ordered_ids: list[int],
) -> None:
    """Reorder teacher-added assignment questions while keeping inherited content fixed."""
    _assert_can_compose(assignment, caller_user)
    teacher_questions = list(
        assignment.questions.filter(origin=AssignmentContentOrigin.TEACHER_ADDITION).order_by(
            "order_index", "id"
        )
    )
    if not teacher_questions:
        raise ValueError("No teacher-added questions are available to reorder.")
    expected_ids = [question.id for question in teacher_questions]
    if sorted(expected_ids) != sorted(ordered_ids) or len(expected_ids) != len(ordered_ids):
        raise ValueError("orderedIds must contain every teacher-added question exactly once.")

    base_order = assignment.questions.filter(origin=AssignmentContentOrigin.TEMPLATE).count()
    question_by_id = {question.id: question for question in teacher_questions}
    for offset, question_id in enumerate(ordered_ids):
        question_by_id[question_id].order_index = base_order + offset
    AssignmentQuestion.objects.bulk_update(list(question_by_id.values()), ["order_index"])


@transaction.atomic
def reorder_assignment_teacher_criteria(
    assignment: Assignment,
    caller_user,
    ordered_ids: list[int],
) -> None:
    """Reorder the teacher-authored rubric overlay criteria for an assignment."""
    _assert_can_compose(assignment, caller_user)
    criteria = list(assignment.teacher_criteria.order_by("order_index", "id"))
    if not criteria:
        raise ValueError("No teacher-added criteria are available to reorder.")
    expected_ids = [criterion.id for criterion in criteria]
    if sorted(expected_ids) != sorted(ordered_ids) or len(expected_ids) != len(ordered_ids):
        raise ValueError("orderedIds must contain every teacher-added criterion exactly once.")

    criterion_by_id = {criterion.id: criterion for criterion in criteria}
    for offset, criterion_id in enumerate(ordered_ids):
        criterion_by_id[criterion_id].order_index = offset
    AssignmentTeacherCriterion.objects.bulk_update(list(criterion_by_id.values()), ["order_index"])


@transaction.atomic
def add_assignment_teacher_criterion_level(
    assignment: Assignment,
    criterion_id: int,
    caller_user,
    payload: dict,
) -> AssignmentTeacherCriterionLevel:
    """Add a teacher-authored level to a teacher-authored criterion."""
    _assert_can_compose(assignment, caller_user)
    criterion = _get_teacher_criterion(assignment, criterion_id)

    label = (payload.get("label") or "").strip()
    if not label:
        raise ValueError("label is required")
    points = payload.get("points")
    if points is None:
        raise ValueError("points is required")

    return AssignmentTeacherCriterionLevel.objects.create(
        criterion=criterion,
        label=label,
        points=points,
        description=(payload.get("description") or "").strip(),
        order_index=_next_teacher_criterion_level_order(criterion),
    )


@transaction.atomic
def reorder_assignment_teacher_criterion_levels(
    assignment: Assignment,
    criterion_id: int,
    caller_user,
    ordered_ids: list[int],
) -> None:
    """Reorder the levels for a teacher-authored criterion."""
    _assert_can_compose(assignment, caller_user)
    criterion = _get_teacher_criterion(assignment, criterion_id)
    levels = list(criterion.levels.order_by("order_index", "id"))
    if not levels:
        raise ValueError("No teacher-added levels are available to reorder.")
    expected_ids = [level.id for level in levels]
    if sorted(expected_ids) != sorted(ordered_ids) or len(expected_ids) != len(ordered_ids):
        raise ValueError("orderedIds must contain every teacher-added level exactly once.")

    level_by_id = {level.id: level for level in levels}
    for offset, level_id in enumerate(ordered_ids):
        level_by_id[level_id].order_index = offset
    AssignmentTeacherCriterionLevel.objects.bulk_update(list(level_by_id.values()), ["order_index"])


def list_reusable_question_images(assignment: Assignment) -> list[dict[str, Any]]:
    """Return reusable question-image metadata visible from the assignment context."""
    seen: dict[str, dict[str, Any]] = {}
    template_questions = Question.objects.filter(
        assignment_template=assignment.assignment_template
    ).exclude(image__isnull=True).exclude(image__exact="")
    assignment_questions = assignment.questions.exclude(image__isnull=True).exclude(image__exact="")
    for question in list(template_questions) + list(assignment_questions):
        meta = _parse_image_meta(question.image)
        if not meta:
            continue
        asset_id = str(meta.get("assetId", ""))
        if asset_id in seen:
            continue
        seen[asset_id] = {
            "id": asset_id,
            "storageKey": meta.get("storageKey", ""),
            "url": f"/api/v1/assignments/images/{meta.get('storageKey', '')}",
            "originalFilename": meta.get("originalFilename", ""),
            "mimeType": meta.get("mimeType", ""),
            "sizeBytes": meta.get("sizeBytes", 0),
        }
    return list(seen.values())


def serialize_assignment_question_image(asset, *, storage_key: str) -> str:
    """Build the shared JSON image metadata payload used by assignment questions."""
    return json.dumps(
        {
            "assetId": str(asset.id),
            "storageKey": storage_key,
            "originalFilename": asset.original_filename,
            "mimeType": asset.mime_type,
            "sizeBytes": asset.size_bytes,
            "sha256Hash": asset.sha256_hash,
        }
    )
