"""
Assessment domain helpers.

This module provides business logic for managing assessment templates including:
- Creating assessments with various question types
- Converting assessments to DTOs for API responses
- Managing rubric relationships between assessments

Assessment types by grading mode:
- AUTO: All questions are auto-gradable (MCQ, number scale)
- MANUAL: All questions require teacher grading
- HYBRID: Mix of auto-gradable and manual questions
- RUBRIC: Assessment serves as a rubric for other assessments
- MOOD_METER: Special check-in assessment with grid selection

Question types:
- MULTIPLE_CHOICE: Select one or more choices with point values
- SHORT_ANSWER: Free text response (manual grading)
- NUMBER_SCALE: Numeric value within a range
- MOOD_METER: Row/column grid selection for emotional check-ins
"""

from collections.abc import Iterable

from django.db import transaction

from accounts.models import User
from assignments.models import Assignment

from .models import (
    Assessment,
    GradingMode,
    McqChoice,
    MoodMeterLabel,
    MoodMeterQuestion,
    MultipleChoiceQuestion,
    NumberScaleQuestion,
    Question,
    QuestionKind,
    ShortAnswerQuestion,
)


def assessment_to_dto(assessment: Assessment) -> dict:
    """
    Convert an Assessment to a full DTO including all questions.

    Args:
        assessment: The Assessment model instance

    Returns:
        Dict with id, title, category, gradingMode, questions, rubricId, rubricAssessmentIds
    """
    return {
        "id": assessment.id,
        "title": assessment.title,
        "category": assessment.category,
        "gradingMode": assessment.grading_mode,
        "questions": [question_to_dto(q) for q in assessment.questions.all()],
        "rubricId": assessment.rubric_id,
        "rubricAssessmentIds": assessment.rubric_assessment_ids or [],
    }


def question_to_dto(question: Question) -> dict:
    """
    Convert a Question to a DTO, handling all question types.

    The data field structure varies by question type:
    - MULTIPLE_CHOICE: {"choices": [...], "selectAll": bool, "correctAnswers": []}
    - SHORT_ANSWER: {"caseSensitive": bool, "trim": bool}
    - NUMBER_SCALE: {"min": int, "max": int, "target": int}
    - MOOD_METER: {"labels": [str]}

    Args:
        question: The Question model instance

    Returns:
        Dict with questionId, id, type, prompt, maxPoints, autoGradable, graded, and
        type-specific data
    """
    data: dict | None = None
    select_all = None
    min_value = None
    max_value = None
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
    elif question.kind == QuestionKind.MOOD_METER:
        data = {
            "labels": [label.label for label in question.mood_meter_labels.all()],
        }

    return {
        "questionId": question.id,
        "id": question.id,
        "type": question.kind,
        "prompt": question.prompt,
        "maxPoints": question.max_points,
        "autoGradable": question.auto_gradable,
        "graded": question.graded,
        "selectAll": select_all,
        "min": min_value,
        "max": max_value,
        "data": data,
    }


@transaction.atomic
def create_assessment(request_user: User, payload: dict) -> Assessment:
    """
    Create a new assessment template.

    For MOOD_METER assessments, delegates to create_mood_meter_assessment which
    creates a special single-question assessment.

    For other types, creates the assessment and all its questions based on the
    payload. Also applies rubric links if the assessment is of RUBRIC type.

    Args:
        request_user: The admin creating the assessment
        payload: Dict with title, gradingMode, questions, category, rubricId, rubricAssessmentIds

    Returns:
        The created Assessment
    """
    grading_mode = payload.get("gradingMode")
    title = payload.get("title")
    if not grading_mode:
        raise ValueError("gradingMode is required")
    if not title:
        raise ValueError("title is required")
    if grading_mode == GradingMode.MOOD_METER:
        return create_mood_meter_assessment(request_user, payload)

    assessment = Assessment.objects.create(
        title=title,
        grading_mode=grading_mode,
        created_by_admin=request_user,
        rubric_id=payload.get("rubricId"),
        rubric_assessment_ids=payload.get("rubricAssessmentIds") or [],
        category=payload.get("category"),
    )
    _replace_questions(assessment, payload.get("questions") or [])
    _apply_rubric_links(assessment)
    return assessment


def create_mood_meter_assessment(request_user: User, payload: dict) -> Assessment:
    """
    Create a mood meter assessment with a pre-configured question.

    Mood meter assessments are special check-in assessments that allow students
    to select how they're feeling on a grid. They always have exactly one
    question with a default prompt.

    Args:
        request_user: The admin creating the assessment
        payload: Dict with title and category

    Returns:
        The created Assessment with its mood meter question
    """
    title = payload.get("title")
    if not title:
        raise ValueError("title is required")
    assessment = Assessment.objects.create(
        title=title,
        grading_mode=GradingMode.MOOD_METER,
        created_by_admin=request_user,
        rubric_id=None,
        rubric_assessment_ids=[],
        category=payload.get("category"),
    )
    question = Question.objects.create(
        assessment=assessment,
        question_type=QuestionKind.MOOD_METER,
        kind=QuestionKind.MOOD_METER,
        prompt="How are you feeling today?",
        max_points=0.0,
        auto_gradable=False,
        graded=False,
    )
    MoodMeterQuestion.objects.create(question=question)
    return assessment


@transaction.atomic
def update_assessment(assessment: Assessment, payload: dict) -> Assessment:
    """
    Update an existing assessment, replacing all questions.

    Note: This replaces all questions, which can invalidate existing submissions
    if question IDs change. Consider locking assessments after submissions exist.

    Args:
        assessment: The Assessment to update
        payload: Dict with title, category, gradingMode, questions, rubricId, rubricAssessmentIds

    Returns:
        The updated Assessment
    """
    assessment.title = payload.get("title", assessment.title)
    assessment.category = payload.get("category")
    assessment.grading_mode = payload.get("gradingMode", assessment.grading_mode)
    assessment.rubric_id = payload.get("rubricId")
    assessment.rubric_assessment_ids = payload.get("rubricAssessmentIds") or []
    assessment.save()
    _replace_questions(assessment, payload.get("questions") or [])
    _apply_rubric_links(assessment)
    return assessment


@transaction.atomic
def delete_assessment(assessment: Assessment) -> None:
    """
    Delete an assessment and all associated assignments.

    Note: This is a hard delete. Consider implementing soft delete for auditability.
    """
    Assignment.objects.filter(assessment=assessment).delete()
    assessment.delete()


def list_assessments() -> list[Assessment]:
    """Return all assessments in the system."""
    return list(Assessment.objects.all())


def _replace_questions(assessment: Assessment, questions: Iterable[dict]) -> None:
    """Delete all existing questions and create new ones from payloads."""
    Question.objects.filter(assessment=assessment).delete()
    for question_payload in questions:
        _create_question(assessment, question_payload)


def _create_question(assessment: Assessment, payload: dict) -> Question:
    """
    Create a Question with its type-specific configuration.

    Each question type has a related model for its settings:
    - MULTIPLE_CHOICE -> MultipleChoiceQuestion + McqChoice records
    - SHORT_ANSWER -> ShortAnswerQuestion
    - NUMBER_SCALE -> NumberScaleQuestion with min/max/target
    - MOOD_METER -> MoodMeterQuestion + MoodMeterLabel records
    """
    kind = payload.get("type")
    if not kind:
        raise ValueError("Question type is required")
    prompt = payload.get("prompt")
    if not prompt:
        raise ValueError("Question prompt is required")
    question = Question.objects.create(
        assessment=assessment,
        question_type=kind,
        kind=kind,
        prompt=prompt,
        max_points=payload.get("maxPoints") or 0,
        auto_gradable=kind in (QuestionKind.MULTIPLE_CHOICE, QuestionKind.NUMBER_SCALE),
        graded=False,
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
    elif kind == QuestionKind.MOOD_METER:
        MoodMeterQuestion.objects.create(question=question)
        for label in data.get("labels", []):
            MoodMeterLabel.objects.create(question=question, label=label)

    return question


def _apply_rubric_links(assessment: Assessment) -> None:
    """
    Link this rubric assessment to its target assessments.

    When an assessment is of type RUBRIC, it can be linked to other assessments
    to provide grading criteria. This function updates the rubric_id field on
    all target assessments listed in rubric_assessment_ids.
    """
    if assessment.grading_mode != GradingMode.RUBRIC:
        return
    if not assessment.rubric_assessment_ids:
        return
    for assessment_id in assessment.rubric_assessment_ids:
        target = Assessment.objects.filter(id=assessment_id).first()
        if target:
            target.rubric_id = assessment.id
            target.save(update_fields=["rubric_id"])
