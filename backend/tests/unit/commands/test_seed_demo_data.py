"""Unit tests for seed_demo_data management command helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.management.commands.seed_demo_data import Command
from submissions.models import SubmissionStatus


def _question(*, kind, max_points=5, data=None):
    """Build a minimal assignment-owned question snapshot for seed helper tests."""
    return SimpleNamespace(kind=kind, max_points=max_points, data=data or {})


def _answer(question):
    """Build a minimal answer object matching the helper's expectations."""
    answer = MagicMock()
    answer.question = question
    answer.score = None
    answer.skipped = True
    return answer


@pytest.mark.unit
@patch("core.management.commands.seed_demo_data.MultipleChoiceSelected")
@patch("core.management.commands.seed_demo_data.MultipleChoiceAnswer")
@patch("core.management.commands.seed_demo_data.Submission")
def test_mark_submission_state_reads_assignment_question_choice_data(
    mock_submission,
    mock_mc_answer,
    mock_mc_selected,
):
    """MCQ seeding uses assignment question JSON choice data, not template relations."""
    question = _question(
        kind="MULTIPLE_CHOICE",
        max_points=4,
        data={
            "choices": [
                {"prompt": "Low", "score": 1},
                {"prompt": "High", "score": 3},
            ]
        },
    )
    answer = _answer(question)
    submission = MagicMock()
    submission.answers.select_related.return_value.all.return_value = [answer]
    mock_submission.objects.filter.return_value.first.return_value = submission

    mc_answer = MagicMock()
    mock_mc_answer.objects.get_or_create.return_value = (mc_answer, True)
    assignment = SimpleNamespace(
        title="Seed Assignment",
        assignment_template=SimpleNamespace(grading_mode="AUTO"),
    )
    student = SimpleNamespace(username="student1")

    Command()._mark_submission_state(
        assignment=assignment,
        student=student,
        status=SubmissionStatus.SUBMITTED,
        short_answer_text="ignored",
    )

    mock_mc_selected.objects.create.assert_called_once_with(
        answer=mc_answer,
        choice_index=1,
    )
    assert answer.score == 3.0
