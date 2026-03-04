"""Shared helpers used across multiple domain modules."""

from assessments.models import QuestionKind
from submissions.models import AnswerType


def answer_type_from_question(question) -> str:
    """Map a question kind to the corresponding answer type."""
    if question.kind == QuestionKind.MULTIPLE_CHOICE:
        return AnswerType.MULTIPLE_CHOICE
    if question.kind == QuestionKind.SHORT_ANSWER:
        return AnswerType.SHORT_ANSWER
    if question.kind == QuestionKind.NUMBER_SCALE:
        return AnswerType.NUMBER_SCALE
    return AnswerType.SHORT_ANSWER
