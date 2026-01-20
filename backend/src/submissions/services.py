"""
Submission domain helpers.

This module provides business logic for managing submissions including:
- Creating and editing submissions
- Auto-scoring based on assessment grading mode
- Manual score overrides by teachers
- Converting submissions to DTOs for API responses

Submission lifecycle:
1. IN_PROGRESS - Student has started but not submitted
2. SUBMITTED - Student has submitted, awaiting grading
3. GRADED - Submission has been scored (auto or manual)
"""

from collections.abc import Iterable

from django.db import transaction
from django.utils import timezone

from assessments.models import Assessment, Question
from assignments.models import Assignment, AudienceType

from .models import (
    Answer,
    AnswerType,
    MoodMeterAnswer,
    MultipleChoiceAnswer,
    MultipleChoiceSelected,
    NumberScaleAnswer,
    ShortAnswerAnswer,
    Submission,
    SubmissionStatus,
)


def submission_to_dto(submission: Submission) -> dict:
    """
    Convert a Submission to a full DTO for API responses.

    Includes all answer details, suitable for viewing/editing a submission.

    Args:
        submission: The Submission model instance

    Returns:
        Dict with id, assignmentId, studentId, teacherId, submittedAt, score, status, answers
    """
    return {
        "id": submission.id,
        "assignmentId": submission.assignment_id,
        "studentId": submission.student_id,
        "teacherId": submission.teacher_id,
        "submittedAt": submission.submitted_at,
        "score": submission.score,
        "status": submission.status,
        "answers": [answer_to_dto(answer) for answer in submission.answers.all()],
    }


def submission_to_compact_dto(submission: Submission) -> dict:
    """
    Convert a Submission to a compact DTO for list views.

    Excludes answer details for performance when listing many submissions.

    Args:
        submission: The Submission model instance

    Returns:
        Dict with id, assignmentId, submittedAt, score, status (no answers)
    """
    return {
        "id": submission.id,
        "assignmentId": submission.assignment_id,
        "submittedAt": submission.submitted_at,
        "score": submission.score,
        "status": submission.status,
    }


def answer_to_dto(answer: Answer) -> dict:
    """
    Convert an Answer to a DTO, handling all answer types.

    The data field structure varies by answer type:
    - MULTIPLE_CHOICE: {"selected": [int indices]}
    - SHORT_ANSWER: {"text": str}
    - NUMBER_SCALE: {"val": int}
    - MOOD_METER: {"row": int, "col": int}

    Args:
        answer: The Answer model instance

    Returns:
        Dict with questionId, type, data, and score
    """
    data: dict
    if answer.answer_type == AnswerType.MULTIPLE_CHOICE:
        selected = list(answer.multiple_choice.selected.values_list("choice_index", flat=True))
        data = {"selected": selected}
    elif answer.answer_type == AnswerType.SHORT_ANSWER:
        data = {"text": answer.short_answer.text}
    elif answer.answer_type == AnswerType.NUMBER_SCALE:
        data = {"val": answer.number_scale.val}
    elif answer.answer_type == AnswerType.MOOD_METER:
        data = {"row": answer.mood_meter.row, "col": answer.mood_meter.col}
    else:
        data = {}
    return {
        "questionId": answer.question_id,
        "type": answer.answer_type,
        "data": data,
        "score": answer.score,
    }


@transaction.atomic
def create_submission(assignment_id: int, payload: dict, status: str) -> Submission:
    """
    Create a new submission for an assignment.

    Handles the complexity of submission creation:
    - For non-MOOD_METER assessments, updates existing submission if one exists
    - For MOOD_METER assessments, always creates a new submission (allows multiple)
    - Auto-scores if the assessment grading mode is AUTO or MOOD_METER
    - Sets submitted_at timestamp if status is not IN_PROGRESS

    Args:
        assignment_id: The assignment being submitted to
        payload: Dict with studentId/teacherId, answers, and optional submittedAt
        status: The submission status (IN_PROGRESS, SUBMITTED, etc.)

    Returns:
        The created or updated Submission

    Raises:
        ValueError: If assignment or assessment not found
    """
    assignment = Assignment.objects.filter(id=assignment_id).first()
    if not assignment:
        raise ValueError("Assignment not found")
    assessment = Assessment.objects.filter(id=assignment.assessment_id).first()
    if not assessment:
        raise ValueError("Assessment not found")

    student_id = payload.get("studentId")
    teacher_id = payload.get("teacherId")

    # MOOD_METER assessments allow multiple submissions (e.g., daily check-ins)
    # Other assessments update the existing submission if one exists
    if assessment.grading_mode != "MOOD_METER":
        existing = _find_existing_submission(assignment_id, student_id, teacher_id)
        if existing:
            payload_with_status = dict(payload)
            payload_with_status["status"] = status
            return edit_submission(payload_with_status)

    submitted_at = payload.get("submittedAt")
    if not submitted_at and status != SubmissionStatus.IN_PROGRESS:
        submitted_at = timezone.now()

    submission = Submission.objects.create(
        assignment=assignment,
        student_id=student_id,
        teacher_id=teacher_id,
        submitted_at=submitted_at,
        status=status,
    )
    _replace_answers(submission, payload.get("answers") or [])
    if status != SubmissionStatus.IN_PROGRESS and assessment.grading_mode != "MANUAL":
        _auto_score_submission(submission, assessment)
    submission.save()
    return submission


@transaction.atomic
def submit_teacher_self_assessment(
    creator_user_id: int,
    assessment_id: int,
    answers: list,
) -> Submission:
    """
    Create a self-assessment submission for a teacher.

    Teachers can submit assessments about themselves (e.g., self-reflection).
    This creates a special assignment with TEACHER audience type and immediately
    creates the submission.

    Args:
        creator_user_id: The teacher's user ID
        assessment_id: The assessment template to use
        answers: List of answer payloads

    Returns:
        The created Submission

    Raises:
        ValueError: If assessment not found
    """
    assessment = Assessment.objects.filter(id=assessment_id).first()
    if not assessment:
        raise ValueError("Assessment not found")

    assignment = Assignment.objects.create(
        assessment_id=assessment_id,
        audience_type=AudienceType.TEACHER,
        course_id=None,
        teacher_id=creator_user_id,
        created_by_id=creator_user_id,
        open_at=timezone.now(),
        due_at=None,
    )

    submission = Submission.objects.create(
        assignment=assignment,
        teacher_id=creator_user_id,
        submitted_at=timezone.now(),
        status=SubmissionStatus.SUBMITTED,
    )
    _replace_answers(submission, answers)
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


def get_by_teacher(teacher_id: int) -> list[Submission]:
    """Get all submissions by a teacher (self-assessments)."""
    return list(Submission.objects.filter(teacher_id=teacher_id))


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


def list_mine(user_id: int, status: str | None) -> list[dict]:
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
    student_subs = Submission.objects.filter(student_id=user_id)
    teacher_subs = Submission.objects.filter(teacher_id=user_id)
    submissions = {sub.id: sub for sub in list(student_subs) + list(teacher_subs)}
    items = list(submissions.values())
    if status:
        items = [sub for sub in items if sub.status == status]
    return [submission_to_compact_dto(sub) for sub in items]


@transaction.atomic
def edit_submission(payload: dict) -> Submission:
    """
    Edit an existing submission with new answers.

    Finds the submission by assignment and student/teacher ID, replaces all
    answers with the new ones, and re-runs auto-scoring if applicable.

    Args:
        payload: Dict with assignmentId, studentId/teacherId, answers, and optionally score/status

    Returns:
        The updated Submission

    Raises:
        ValueError: If submission not found
    """
    assignment_id = payload.get("assignmentId")
    student_id = payload.get("studentId")
    teacher_id = payload.get("teacherId")
    if assignment_id is None:
        raise ValueError("assignmentId is required")
    submission = _find_existing_submission(assignment_id, student_id, teacher_id)
    if not submission:
        raise ValueError("Submission not found")

    submission.submitted_at = timezone.now()
    submission.score = payload.get("score")
    status = payload.get("status") or submission.status
    submission.status = status
    _replace_answers(submission, payload.get("answers") or [])

    assessment = Assessment.objects.filter(id=submission.assignment.assessment_id).first()
    if (
        assessment
        and status != SubmissionStatus.IN_PROGRESS
        and assessment.grading_mode != "MANUAL"
    ):
        _auto_score_submission(submission, assessment)

    submission.save()
    return submission


@transaction.atomic
def override_score(submission_id: int, scores: list) -> Submission:
    """
    Manually override scores for a submission (teacher grading).

    Handles three grading modes differently:
    - MOOD_METER: Just marks as graded (no actual scores)
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
    submission = Submission.objects.filter(id=submission_id).first()
    if not submission:
        raise ValueError("Submission not found")
    if not scores:
        raise ValueError("Override score request must include score values")

    assessment = Assessment.objects.filter(id=submission.assignment.assessment_id).first()
    if not assessment:
        raise ValueError("Assessment not found")

    answers = list(submission.answers.all())
    total = 0.0

    # MOOD_METER assessments have no numeric scoring - just mark as graded
    if assessment.grading_mode == "MOOD_METER":
        submission.status = SubmissionStatus.GRADED
        if submission.submitted_at is None:
            submission.submitted_at = timezone.now()
        submission.save()
        return submission

    # HYBRID mode: only manually score SHORT_ANSWER questions
    # Other question types (MCQ, NUMBER_SCALE) keep their auto-calculated scores
    if assessment.grading_mode == "HYBRID":
        score_index = 0
        for answer in answers:
            if answer.answer_type == AnswerType.SHORT_ANSWER and score_index < len(scores):
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
    - MOOD_METER -> MoodMeterAnswer with row/col grid position
    """
    question_id = payload.get("questionId")
    if question_id is None:
        raise ValueError("Question ID is required")
    question = Question.objects.filter(id=question_id).first()
    if not question:
        raise ValueError("Question not found")
    answer_type = payload.get("type")
    if not answer_type:
        raise ValueError("Answer type is required")
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
    elif answer_type == AnswerType.MOOD_METER:
        MoodMeterAnswer.objects.create(
            answer=answer, row=data.get("row", 0), col=data.get("col", 0)
        )
    return answer


def _auto_score_submission(submission: Submission, assessment: Assessment) -> None:
    """
    Calculate auto-scores for all gradable answers in a submission.

    Only processes answers where the question is marked auto_gradable.
    Currently supports auto-scoring for MULTIPLE_CHOICE and NUMBER_SCALE.
    SHORT_ANSWER requires manual grading.

    For AUTO and MOOD_METER grading modes, also marks the submission as GRADED.
    """
    total = 0.0
    for answer in submission.answers.all():
        question = answer.question
        if not question.auto_gradable:
            continue
        if answer.answer_type == AnswerType.MULTIPLE_CHOICE:
            total += _auto_score_mcq(answer, question)
        elif answer.answer_type == AnswerType.NUMBER_SCALE:
            total += _auto_score_number_scale(answer, question)
    submission.score = total
    if assessment.grading_mode in ("AUTO", "MOOD_METER"):
        submission.status = SubmissionStatus.GRADED
        if submission.submitted_at is None:
            submission.submitted_at = timezone.now()


def _auto_score_mcq(answer: Answer, question: Question) -> float:
    """
    Auto-score a multiple choice answer by summing points for selected choices.

    Each choice has an associated point value. The score is the sum of points
    for all selected choices.
    """
    choices = list(question.mcq_choices.all())
    selected = list(answer.multiple_choice.selected.values_list("choice_index", flat=True))
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
    """
    target = question.number_scale.target
    if target is None:
        return 0.0
    val = answer.number_scale.val
    score = question.max_points if val == target else 0.0
    answer.score = score
    answer.save(update_fields=["score"])
    return score
