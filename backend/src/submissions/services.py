"""
Submission domain helpers.

This module provides business logic for managing submissions including:
- Creating and editing submissions
- Auto-scoring based on assessment grading mode
- Manual score overrides by teachers
- Converting submissions to DTOs for API responses

Submission lifecycle:
    NOT_STARTED -> IN_PROGRESS -> SUBMITTED -> GRADED
"""

from collections.abc import Iterable

from django.db import transaction
from django.db.models import Prefetch, QuerySet
from django.utils import timezone

from assessments.models import Assessment, GradingMode, McqChoice, Question, ScoringPolicy
from assignments.models import Assignment
from core.dtos import AnswerDTO, SubmissionCompactDTO, SubmissionDTO

from .models import (
    Answer,
    AnswerType,
    MultipleChoiceAnswer,
    MultipleChoiceSelected,
    NumberScaleAnswer,
    ShortAnswerAnswer,
    Submission,
    SubmissionStatus,
)


# ── Prefetch helpers ──────────────────────────────────────────────────

# Shared prefetch paths for answer sub-types used by DTO serialization.
_ANSWER_SUBTYPE_PREFETCHES = [
    "answers__multiple_choice__selected",
    "answers__short_answer",
    "answers__number_scale",
]

# Extended prefetch paths that also pull question + mcq_choices for scoring.
_ANSWER_SCORING_PREFETCHES = [
    *_ANSWER_SUBTYPE_PREFETCHES,
    "answers__question__mcq_choices",
    "answers__question__number_scale",
]


def _prefetch_submission_for_dto(qs: QuerySet[Submission]) -> QuerySet[Submission]:
    """Add prefetches needed to serialize submissions to DTOs without N+1."""
    return qs.prefetch_related(*_ANSWER_SUBTYPE_PREFETCHES)


def _prefetch_submission_for_scoring(qs: QuerySet[Submission]) -> QuerySet[Submission]:
    """Add prefetches needed to auto-score submissions without N+1."""
    return qs.prefetch_related(*_ANSWER_SCORING_PREFETCHES)


def get_submission_for_dto(submission_id: int) -> Submission:
    """Retrieve a single submission with answer sub-types prefetched for DTO conversion.

    Raises:
        ValueError: If submission not found
    """
    submission = _prefetch_submission_for_dto(
        Submission.objects.filter(id=submission_id)
    ).first()
    if not submission:
        raise ValueError("Submission not found")
    return submission


def get_by_student_and_assignment_for_dto(student_id: int, assignment_id: int) -> Submission:
    """Get a student's submission with answer prefetches for DTO conversion.

    Raises:
        ValueError: If no submission exists
    """
    submission = _prefetch_submission_for_dto(
        Submission.objects.filter(student_id=student_id, assignment_id=assignment_id)
    ).first()
    if not submission:
        raise ValueError("Submission not found")
    return submission

# Valid forward transitions in the submission state machine (SUB-CN-01).
_VALID_TRANSITIONS: dict[str, set[str]] = {
    SubmissionStatus.NOT_STARTED: {SubmissionStatus.IN_PROGRESS, SubmissionStatus.SUBMITTED},
    SubmissionStatus.IN_PROGRESS: {SubmissionStatus.IN_PROGRESS, SubmissionStatus.SUBMITTED},
    SubmissionStatus.SUBMITTED: {SubmissionStatus.GRADED},
    SubmissionStatus.GRADED: set(),
}


def submission_to_dto(submission: Submission) -> SubmissionDTO:
    """
    Convert a Submission to a full DTO for API responses.

    Includes all answer details, suitable for viewing/editing a submission.

    Args:
        submission: The Submission model instance

    Returns:
        SubmissionDTO with id, assignmentId, studentId, teacherId, submittedAt,
        score, status, and answers.
    """
    return SubmissionDTO(
        id=submission.id,
        assignmentId=submission.assignment_id,
        studentId=submission.student_id,
        teacherId=submission.teacher_id,
        submittedAt=submission.submitted_at,
        score=submission.score,
        status=submission.status,
        answers=[answer_to_dto(answer) for answer in submission.answers.all()],
    )


def submission_to_compact_dto(submission: Submission) -> SubmissionCompactDTO:
    """
    Convert a Submission to a compact DTO for list views.

    Excludes answer details for performance when listing many submissions.

    Args:
        submission: The Submission model instance

    Returns:
        SubmissionCompactDTO with id, assignmentId, submittedAt, score, status (no answers)
    """
    return SubmissionCompactDTO(
        id=submission.id,
        assignmentId=submission.assignment_id,
        submittedAt=submission.submitted_at,
        score=submission.score,
        status=submission.status,
    )


def answer_to_dto(answer: Answer) -> AnswerDTO:
    """
    Convert an Answer to a DTO, handling all answer types.

    The data field structure varies by answer type:
    - MULTIPLE_CHOICE: {"selected": [int indices]}
    - SHORT_ANSWER: {"text": str}
    - NUMBER_SCALE: {"val": int}

    Args:
        answer: The Answer model instance

    Returns:
        AnswerDTO with questionId, type, data, and score
    """
    data: dict
    if answer.answer_type == AnswerType.MULTIPLE_CHOICE:
        # Use .all() to leverage prefetch cache instead of values_list() which always queries.
        selected = [sel.choice_index for sel in answer.multiple_choice.selected.all()]
        data = {"selected": selected}
    elif answer.answer_type == AnswerType.SHORT_ANSWER:
        data = {"text": answer.short_answer.text}
    elif answer.answer_type == AnswerType.NUMBER_SCALE:
        data = {"val": answer.number_scale.val}
    else:
        data = {}
    return AnswerDTO(
        questionId=answer.question_id,
        type=answer.answer_type,
        data=data,
        score=answer.score,
    )


@transaction.atomic
def create_submission(assignment_id: int, payload: dict, target_status: str) -> Submission:
    """
    Create or update a submission for an assignment.

    If a submission already exists for this student+assignment, delegates to
    edit_submission. Otherwise creates a new Submission.

    State machine enforced (SUB-CN-01). submitted_at only set at SUBMITTED+.
    """
    assignment = Assignment.objects.filter(id=assignment_id).first()
    if not assignment:
        raise ValueError("Assignment not found")
    assessment = Assessment.objects.filter(id=assignment.assessment_id).first()
    if not assessment:
        raise ValueError("Assessment not found")

    student_id = payload.get("studentId")
    teacher_id = payload.get("teacherId")

    existing = _find_existing_submission(assignment_id, student_id, teacher_id)
    if existing:
        payload_with_status = dict(payload)
        payload_with_status["status"] = target_status
        return edit_submission(payload_with_status)

    # Only set submitted_at for SUBMITTED or beyond
    submitted_at = None
    if target_status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED):
        submitted_at = payload.get("submittedAt") or timezone.now()

    submission = Submission.objects.create(
        assignment=assignment,
        student_id=student_id,
        teacher_id=teacher_id,
        submitted_at=submitted_at,
        status=target_status,
    )
    _replace_answers(submission, payload.get("answers") or [])
    if target_status != SubmissionStatus.IN_PROGRESS and (
        assessment.scoring_policy == ScoringPolicy.COMPLETION
        or assessment.grading_mode != GradingMode.MANUAL
    ):
        _auto_score_submission(submission, assessment)
    submission.save()
    return submission


def get_submission(submission_id: int) -> Submission:
    """
    Retrieve a single submission by ID.

    Args:
        submission_id: The submission's primary key

    Returns:
        The Submission object

    Raises:
        ValueError: If submission not found
    """
    submission = Submission.objects.filter(id=submission_id).first()
    if not submission:
        raise ValueError("Submission not found")
    return submission


def get_by_assignment(assignment_id: int) -> list[Submission]:
    """Get all submissions for an assignment."""
    return list(Submission.objects.filter(assignment_id=assignment_id))


def get_by_student(student_id: int) -> list[Submission]:
    """Get all submissions by a student across all assignments."""
    return list(Submission.objects.filter(student_id=student_id))


def get_by_student_and_assignment(student_id: int, assignment_id: int) -> Submission:
    """
    Get a student's submission for a specific assignment.

    Args:
        student_id: The student's user ID
        assignment_id: The assignment ID

    Returns:
        The Submission object

    Raises:
        ValueError: If no submission exists
    """
    submission = Submission.objects.filter(
        student_id=student_id,
        assignment_id=assignment_id,
    ).first()
    if not submission:
        raise ValueError("Submission not found")
    return submission


def list_me(user_id: int, status: str | None) -> list[dict]:
    """
    List all submissions for a user, whether as student or teacher.

    Combines submissions where the user is the student with submissions
    where the user is the teacher (self-assessments). Optionally filters
    by submission status.

    Args:
        user_id: The user's ID
        status: Optional status filter (IN_PROGRESS, SUBMITTED, GRADED)

    Returns:
        List of compact submission DTOs
    """
    from django.db.models import Q

    qs = Submission.objects.filter(Q(student_id=user_id) | Q(teacher_id=user_id))
    if status:
        qs = qs.filter(status=status)
    items = list(qs)
    # Sort newest submissions first, with undated drafts last.
    items.sort(key=lambda s: (s.submitted_at is not None, s.submitted_at), reverse=True)
    return [submission_to_compact_dto(sub).model_dump() for sub in items]


@transaction.atomic
def edit_submission(payload: dict) -> Submission:
    """
    Edit an existing submission with new answers.

    Finds the submission by assignment and student/teacher ID, replaces all
    answers with the new ones, and re-runs auto-scoring if applicable.

    State machine enforced: only forward transitions allowed (SUB-CN-01).
    submitted_at only set when transitioning to SUBMITTED or beyond.
    """
    assignment_id = payload.get("assignmentId")
    student_id = payload.get("studentId")
    teacher_id = payload.get("teacherId")
    if assignment_id is None:
        raise ValueError("assignmentId is required")
    submission = _find_existing_submission(assignment_id, student_id, teacher_id)
    if not submission:
        raise ValueError("Submission not found")

    new_status = payload.get("status") or submission.status
    _validate_transition(submission.status, new_status)

    submission.status = new_status
    submission.score = payload.get("score")

    # Only set submitted_at when reaching SUBMITTED or beyond
    if new_status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED) and not submission.submitted_at:
        submission.submitted_at = timezone.now()

    _replace_answers(submission, payload.get("answers") or [])

    assessment = Assessment.objects.filter(id=submission.assignment.assessment_id).first()
    if (
        assessment
        and new_status != SubmissionStatus.IN_PROGRESS
        and (
            assessment.scoring_policy == ScoringPolicy.COMPLETION
            or assessment.grading_mode != GradingMode.MANUAL
        )
    ):
        _auto_score_submission(submission, assessment)

    submission.save()
    return submission


@transaction.atomic
def override_score(submission_id: int, scores: list) -> Submission:
    """
    Manually override scores for a submission (teacher grading).

    Handles three grading modes differently:
    - HYBRID: Only scores SHORT_ANSWER questions manually, others keep auto-scores
    - MANUAL/other: Applies scores to all answers in order

    The scores list interpretation depends on grading mode:
    - HYBRID: scores[i] applies to the i-th SHORT_ANSWER question
    - Other modes: scores[i] applies to answer[i]
    - If more scores than answers, the last score is added to total (bonus points)

    Args:
        submission_id: The submission to grade
        scores: List of numeric scores to apply

    Returns:
        The updated Submission with new scores and GRADED status

    Raises:
        ValueError: If submission not found, no scores provided, or assessment not found
    """
    submission = (
        Submission.objects.select_related("assignment__assessment")
        .filter(id=submission_id)
        .first()
    )
    if not submission:
        raise ValueError("Submission not found")
    if not scores:
        raise ValueError("Override score request must include score values")

    assessment = submission.assignment.assessment
    if not assessment:
        raise ValueError("Assessment not found")
    if assessment.scoring_policy == ScoringPolicy.COMPLETION:
        raise ValueError(
            "Completion-scored assessments always award full credit and cannot be manually overridden"
        )

    answers = list(submission.answers.all())
    total = 0.0

    # Build a lookup for max_points per question so we can validate scores.
    question_ids = [a.question_id for a in answers]
    max_pts_map = dict(
        Question.objects.filter(id__in=question_ids).values_list("id", "max_points")
    )

    def _validate_score(answer, score_val):
        cap = max_pts_map.get(answer.question_id)
        if cap is not None and score_val > cap:
            raise ValueError(
                f"Score {score_val} exceeds max points ({cap}) for question {answer.question_id}"
            )

    # HYBRID mode: only manually score SHORT_ANSWER questions
    # Other question types (MCQ, NUMBER_SCALE) keep their auto-calculated scores
    if assessment.grading_mode == GradingMode.HYBRID:
        score_index = 0
        for answer in answers:
            if answer.answer_type == AnswerType.SHORT_ANSWER and score_index < len(scores):
                _validate_score(answer, scores[score_index])
                answer.score = scores[score_index]
                score_index += 1
            total += answer.score or 0.0
        # If extra scores remain, add the last one as bonus points
        if score_index != len(scores):
            total += scores[-1]
    else:
        # MANUAL and other modes: apply scores to answers in order
        for idx, answer in enumerate(answers):
            if idx < len(scores):
                _validate_score(answer, scores[idx])
                answer.score = scores[idx]
            total += answer.score or 0.0
        # Extra scores beyond answer count are added as bonus
        if len(scores) > len(answers):
            total += scores[-1]

    Answer.objects.bulk_update(answers, ["score"])
    submission.score = total
    submission.status = SubmissionStatus.GRADED
    if submission.submitted_at is None:
        submission.submitted_at = timezone.now()
    submission.save()
    return submission


def _validate_transition(current: str, target: str) -> None:
    """Enforce the submission state machine (SUB-CN-01)."""
    allowed = _VALID_TRANSITIONS.get(current, set())
    if target not in allowed and target != current:
        raise ValueError(
            f"Invalid status transition: {current} -> {target}"
        )


def _find_existing_submission(
    assignment_id: int, student_id: int | None, teacher_id: int | None
) -> Submission | None:
    """Find an existing submission for an assignment and user."""
    if student_id is not None:
        return Submission.objects.filter(assignment_id=assignment_id, student_id=student_id).first()
    if teacher_id is not None:
        return Submission.objects.filter(assignment_id=assignment_id, teacher_id=teacher_id).first()
    return None


def _replace_answers(submission: Submission, answers: Iterable[dict]) -> None:
    """Delete all existing answers and create new ones from payloads."""
    Answer.objects.filter(submission=submission).delete()
    for answer_payload in answers:
        _create_answer(submission, answer_payload)


def _create_answer(submission: Submission, payload: dict) -> Answer:
    """
    Create an Answer record with the appropriate type-specific sub-record.

    Each answer type has a related model for its data:
    - MULTIPLE_CHOICE -> MultipleChoiceAnswer with MultipleChoiceSelected records
    - SHORT_ANSWER -> ShortAnswerAnswer with text
    - NUMBER_SCALE -> NumberScaleAnswer with numeric value
    """
    question_id = payload.get("questionId")
    if question_id is None:
        raise ValueError("Question ID is required")
    question = Question.objects.filter(id=question_id).first()
    if not question:
        raise ValueError("Question not found")
    # Bug 2 fix: verify question belongs to the submission's assignment's assessment
    if question.assessment_id != submission.assignment.assessment_id:
        raise ValueError(
            f"Question {question_id} does not belong to assessment "
            f"{submission.assignment.assessment_id}"
        )
    answer_type = payload.get("type")
    if not answer_type:
        raise ValueError("Answer type is required")
    # Bug 3 fix: verify answer type matches question kind
    if answer_type != question.question_type:
        raise ValueError(
            f"Answer type mismatch: payload type '{answer_type}' does not match "
            f"question type '{question.question_type}'"
        )
    answer = Answer.objects.create(
        submission=submission,
        question=question,
        answer_type=answer_type,
        score=payload.get("score"),
        skipped=False,
    )
    data = payload.get("data") or {}

    if answer_type == AnswerType.MULTIPLE_CHOICE:
        mc = MultipleChoiceAnswer.objects.create(answer=answer)
        for idx in data.get("selected", []):
            MultipleChoiceSelected.objects.create(answer=mc, choice_index=idx)
    elif answer_type == AnswerType.SHORT_ANSWER:
        ShortAnswerAnswer.objects.create(answer=answer, text=data.get("text", ""))
    elif answer_type == AnswerType.NUMBER_SCALE:
        NumberScaleAnswer.objects.create(answer=answer, val=data.get("val"))
    return answer


def _auto_score_submission(submission: Submission, assessment: Assessment) -> None:
    """
    Calculate auto-scores for all gradable answers in a submission.

    Only processes answers where the question is marked auto_gradable.
    Currently supports auto-scoring for MULTIPLE_CHOICE and NUMBER_SCALE.
    SHORT_ANSWER requires manual grading.

    For AUTO grading mode, also marks the submission as GRADED.
    """
    if assessment.scoring_policy == ScoringPolicy.COMPLETION:
        submission.score = 100.0
        submission.status = SubmissionStatus.GRADED
        if submission.submitted_at is None:
            submission.submitted_at = timezone.now()
        return

    # Prefetch answers with question + mcq_choices + number_scale to avoid N+1.
    answers = list(
        submission.answers
        .select_related("question__number_scale")
        .prefetch_related("question__mcq_choices", "multiple_choice__selected")
    )

    total = 0.0
    for answer in answers:
        question = answer.question
        if not question.auto_gradable:
            continue
        if answer.answer_type == AnswerType.MULTIPLE_CHOICE:
            total += _auto_score_mcq(answer, question)
        elif answer.answer_type == AnswerType.NUMBER_SCALE:
            total += _auto_score_number_scale(answer, question)
    submission.score = total
    if assessment.grading_mode == GradingMode.AUTO:
        submission.status = SubmissionStatus.GRADED
        if submission.submitted_at is None:
            submission.submitted_at = timezone.now()


def _auto_score_mcq(answer: Answer, question: Question) -> float:
    """
    Auto-score a multiple choice answer by summing points for selected choices.

    Each choice has an associated point value. The score is the sum of points
    for all selected choices.

    Expects question.mcq_choices and answer.multiple_choice.selected to be
    prefetched by the caller.
    """
    choices = list(question.mcq_choices.all())  # hits prefetch cache
    selected = [sel.choice_index for sel in answer.multiple_choice.selected.all()]
    score = 0.0
    for idx in selected:
        if idx is None or idx < 0 or idx >= len(choices):
            continue
        score += choices[idx].points
    answer.score = score
    answer.save(update_fields=["score"])
    return score


def _auto_score_number_scale(answer: Answer, question: Question) -> float:
    """
    Auto-score a number scale answer by comparing to the target value.

    Full points are awarded only if the answer exactly matches the target.
    If no target is set, returns 0.

    Expects question.number_scale to be select_related by the caller.
    """
    target = question.number_scale.target
    if target is None:
        return 0.0
    val = answer.number_scale.val
    score = question.max_points if val == target else 0.0
    answer.score = score
    answer.save(update_fields=["score"])
    return score
