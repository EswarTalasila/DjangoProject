"""Shared helpers used across multiple domain modules."""

from assignment_templates.models import QuestionKind
from submissions.models import AnswerType


def answer_type_from_question(question) -> str:
    """Map a question kind to the corresponding answer type."""
    if question.kind == QuestionKind.MULTIPLE_CHOICE:
        return AnswerType.MULTIPLE_CHOICE
    if question.kind == QuestionKind.SHORT_ANSWER:
        return AnswerType.SHORT_ANSWER
    if question.kind == QuestionKind.NUMBER_SCALE:
        return AnswerType.NUMBER_SCALE
    if question.kind == QuestionKind.MOOD_METER:
        return AnswerType.MOOD_METER
    if question.kind == QuestionKind.FILE_UPLOAD:
        return AnswerType.FILE_UPLOAD
    return AnswerType.SHORT_ANSWER
