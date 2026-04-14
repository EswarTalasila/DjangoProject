"""Unit tests for submissions.services business logic.

All database access is mocked so tests run without a live database.
"""

from __future__ import annotations

from types import SimpleNamespace
from django.core.exceptions import ObjectDoesNotExist
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from assignment_templates.models import GradingMode
from submissions.models import AnswerType, SubmissionStatus

pytestmark = pytest.mark.unit



@pytest.fixture(autouse=True)
def _patch_transaction_atomic(monkeypatch):
    """Prevent @transaction.atomic wrappers from touching a real DB connection."""
    monkeypatch.setattr("django.db.transaction.Atomic.__enter__", lambda self: None)
    monkeypatch.setattr(
        "django.db.transaction.Atomic.__exit__", lambda self, exc_type, exc, tb: False
    )
    monkeypatch.setattr("django.db.transaction.on_commit", lambda func, using=None: func())


# ---------------------------------------------------------------------------
# Helpers -- tiny mock builders
# ---------------------------------------------------------------------------


def _mock_submission(
    *,
    id=1,
    assignment_id=10,
    assignment_template_id=20,
    student_id=100,
    teacher_id=None,
    submitted_at=None,
    score=None,
    status=SubmissionStatus.SUBMITTED,
    answers=None,
):
    """Build a lightweight mock Submission."""
    sub = MagicMock()
    sub.id = id
    sub.assignment_id = assignment_id
    sub.assignment.assignment_template_id = assignment_template_id
    sub.student_id = student_id
    sub.student = SimpleNamespace(name="Test Student", username="test-student") if student_id else None
    sub.teacher_id = teacher_id
    sub.teacher = None
    sub.assignment.title = "Mock Assignment"
    sub.assignment.course = SimpleNamespace(name="Mock Course")
    sub.assignment.assignment_template_id = assignment_template_id
    sub.submitted_at = submitted_at
    sub.score = score
    sub.status = status
    answer_list = answers or []
    sub.answers = MagicMock()
    sub.answers.all.return_value = answer_list
    sub.answers.order_by.return_value = MagicMock()
    sub.answers.order_by.return_value.values_list.return_value = [
        a.score for a in answer_list
    ]
    # Support chained .select_related() used by override_score (iterable)
    # and .select_related().prefetch_related() used by _auto_score_submission.
    sr_mock = MagicMock()
    sr_mock.__iter__ = lambda self: iter(answer_list)
    sr_mock.prefetch_related.return_value = answer_list
    sub.answers.select_related.return_value = sr_mock
    return sub


def _mock_answer(*, answer_type, question_id=1, score=None, max_points=100.0):
    """Build a lightweight mock Answer with the given type."""
    answer = MagicMock()
    answer.answer_type = answer_type
    answer.question_id = question_id
    answer.score = score
    answer.question.max_points = max_points
    return answer


def _mock_assignment(*, id=10, assignment_template_id=20):
    """Build a lightweight mock Assignment."""
    a = MagicMock()
    a.id = id
    a.assignment_template_id = assignment_template_id
    return a


def _mock_assessment(*, id=20, grading_mode=GradingMode.AUTO):
    """Build a lightweight mock AssignmentTemplate."""
    a = MagicMock()
    a.id = id
    a.grading_mode = grading_mode
    return a


def _mock_question(*, id=1, auto_gradable=True, max_points=5.0, assignment_template_id=20, question_type="SHORT_ANSWER"):
    """Build a lightweight mock Question."""
    q = MagicMock()
    q.id = id
    q.auto_gradable = auto_gradable
    q.max_points = max_points
    q.assignment_template_id = assignment_template_id
    q.question_type = question_type
    return q


# ============================================================================
# submission_to_dto
# ============================================================================


class TestSubmissionToDto:
    """Tests for submission_to_dto conversion."""

    def test_converts_basic_fields(self):
        """All scalar fields are mapped correctly."""
        from submissions.services import submission_to_dto

        now = timezone.now()
        sub = _mock_submission(
            id=42,
            assignment_id=7,
            student_id=99,
            teacher_id=None,
            submitted_at=now,
            score=85.0,
            status=SubmissionStatus.GRADED,
        )
        dto = submission_to_dto(sub)

        assert dto.id == 42
        assert dto.assignmentId == 7
        assert dto.studentId == 99
        assert dto.teacherId is None
        assert dto.submittedAt == now
        assert dto.score == 85.0
        assert dto.status == SubmissionStatus.GRADED

    def test_includes_answers(self):
        """Answer DTOs are generated for each answer in submission."""
        from submissions.services import submission_to_dto

        ans1 = _mock_answer(answer_type=AnswerType.SHORT_ANSWER, question_id=5, score=3.0)
        ans1.short_answer = SimpleNamespace(text="hello")
        sub = _mock_submission(answers=[ans1])

        dto = submission_to_dto(sub)

        assert len(dto.answers) == 1
        assert dto.answers[0].questionId == 5
        assert dto.answers[0].data == {"text": "hello"}

    def test_empty_answers(self):
        """Submission with no answers yields an empty list in the DTO."""
        from submissions.services import submission_to_dto

        sub = _mock_submission(answers=[])
        dto = submission_to_dto(sub)
        assert dto.answers == []


# ============================================================================
# submission_to_compact_dto
# ============================================================================


class TestSubmissionToCompactDto:
    """Tests for the compact (no-answers) DTO conversion."""

    def test_converts_compact_fields(self):
        """Compact DTO contains id, assignmentId, submittedAt, score, status."""
        from submissions.services import submission_to_compact_dto

        sub = _mock_submission(id=5, assignment_id=6, score=10.0, status=SubmissionStatus.GRADED)
        dto = submission_to_compact_dto(sub)

        assert dto.id == 5
        assert dto.assignmentId == 6
        assert dto.score == 10.0
        assert dto.status == SubmissionStatus.GRADED


# ============================================================================
# answer_to_dto
# ============================================================================


class TestAnswerToDto:
    """Tests for answer_to_dto handling each answer type."""

    def test_multiple_choice_answer(self):
        """MCQ answer produces selected indices in data."""
        from submissions.services import answer_to_dto

        ans = _mock_answer(answer_type=AnswerType.MULTIPLE_CHOICE, question_id=3, score=2.0)
        mc = MagicMock()
        sel0 = SimpleNamespace(choice_index=0)
        sel2 = SimpleNamespace(choice_index=2)
        mc.selected.all.return_value = [sel0, sel2]
        ans.multiple_choice = mc

        dto = answer_to_dto(ans)

        assert dto.type == AnswerType.MULTIPLE_CHOICE
        assert dto.data == {"selected": [0, 2]}
        assert dto.score == 2.0
        assert dto.questionId == 3

    def test_short_answer(self):
        """Short answer produces text in data."""
        from submissions.services import answer_to_dto

        ans = _mock_answer(answer_type=AnswerType.SHORT_ANSWER, question_id=4)
        ans.short_answer = SimpleNamespace(text="My essay response")

        dto = answer_to_dto(ans)

        assert dto.data == {"text": "My essay response"}

    def test_number_scale(self):
        """Number scale answer produces val in data."""
        from submissions.services import answer_to_dto

        ans = _mock_answer(answer_type=AnswerType.NUMBER_SCALE, question_id=5)
        ans.number_scale = SimpleNamespace(val=7)

        dto = answer_to_dto(ans)

        assert dto.data == {"val": 7}

    def test_short_answer_missing_subrecord_returns_empty_data(self):
        """Missing short-answer subtype should not crash DTO conversion."""
        from submissions.services import answer_to_dto

        class BrokenShortAnswer:
            answer_type = AnswerType.SHORT_ANSWER
            question_id = 4
            score = None

            @property
            def short_answer(self):
                raise ObjectDoesNotExist("err")

        ans = BrokenShortAnswer()

        dto = answer_to_dto(ans)

        assert dto.data == {}

    def test_unknown_type_returns_empty_data(self):
        """Unrecognized answer type yields an empty dict."""
        from submissions.services import answer_to_dto

        ans = _mock_answer(answer_type="UNKNOWN_TYPE", question_id=7)
        dto = answer_to_dto(ans)

        assert dto.data == {}


# ============================================================================
# create_submission
# ============================================================================


class TestCreateSubmission:
    """Tests for the create_submission service function."""

    @patch("submissions.services._auto_score_submission")
    @patch("submissions.services._replace_answers")
    @patch("submissions.services.Submission")
    @patch("submissions.services.AssignmentTemplate")
    @patch("submissions.services.Assignment")
    def test_raises_when_assignment_not_found(
        self, mock_assign_model, mock_assess_model, mock_sub, _replace, _auto
    ):
        """ValueError raised when assignment_id does not exist."""
        from submissions.services import create_submission

        mock_assign_model.objects.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Assignment not found"):
            create_submission(999, {"studentId": 1}, SubmissionStatus.SUBMITTED)

    @patch("submissions.services._auto_score_submission")
    @patch("submissions.services._replace_answers")
    @patch("submissions.services.Submission")
    @patch("submissions.services.AssignmentTemplate")
    @patch("submissions.services.Assignment")
    def test_raises_when_assessment_not_found(
        self, mock_assign_model, mock_assess_model, mock_sub, _replace, _auto
    ):
        """ValueError raised when linked assignment_template does not exist."""
        from submissions.services import create_submission

        assignment = _mock_assignment()
        mock_assign_model.objects.filter.return_value.first.return_value = assignment
        mock_assess_model.objects.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="AssignmentTemplate not found"):
            create_submission(10, {"studentId": 1}, SubmissionStatus.SUBMITTED)

    @patch("submissions.services._auto_score_submission")
    @patch("submissions.services._replace_answers")
    @patch("submissions.services.Submission")
    @patch("submissions.services.AssignmentTemplate")
    @patch("submissions.services.Assignment")
    @patch("submissions.services._find_existing_submission")
    def test_updates_existing_for_non_mood_meter(
        self, mock_find, mock_assign, mock_assess, mock_sub, _replace, _auto
    ):
        """Non-MOOD_METER assignment_template redirects to edit_submission if submission exists."""
        from submissions.services import create_submission

        assignment = _mock_assignment()
        assignment_template = _mock_assessment(grading_mode=GradingMode.AUTO)
        existing_sub = _mock_submission()

        mock_assign.objects.filter.return_value.first.return_value = assignment
        mock_assess.objects.filter.return_value.first.return_value = assignment_template
        mock_find.return_value = existing_sub

        with patch("submissions.services.edit_submission") as mock_edit:
            mock_edit.return_value = existing_sub
            result = create_submission(10, {"studentId": 1}, SubmissionStatus.SUBMITTED)

        mock_edit.assert_called_once()
        assert result is existing_sub

    @patch("submissions.services._auto_score_submission")
    @patch("submissions.services._replace_answers")
    @patch("submissions.services.Submission")
    @patch("submissions.services.AssignmentTemplate")
    @patch("submissions.services.Assignment")
    @patch("submissions.services._find_existing_submission")
    def test_auto_score_called_for_auto_mode(
        self, mock_find, mock_assign, mock_assess, mock_sub, mock_replace, mock_auto
    ):
        """Auto-scoring runs when status is not IN_PROGRESS and grading is not MANUAL."""
        from submissions.services import create_submission

        assignment = _mock_assignment()
        assignment_template = _mock_assessment(grading_mode=GradingMode.AUTO)
        new_sub = _mock_submission()

        mock_assign.objects.filter.return_value.first.return_value = assignment
        mock_assess.objects.filter.return_value.first.return_value = assignment_template
        mock_find.return_value = None
        mock_sub.objects.create.return_value = new_sub

        create_submission(10, {"studentId": 1}, SubmissionStatus.SUBMITTED)

        mock_auto.assert_called_once_with(new_sub, assignment_template)

    @patch("submissions.services._auto_score_submission")
    @patch("submissions.services._replace_answers")
    @patch("submissions.services.Submission")
    @patch("submissions.services.AssignmentTemplate")
    @patch("submissions.services.Assignment")
    @patch("submissions.services._find_existing_submission")
    def test_no_auto_score_for_in_progress(
        self, mock_find, mock_assign, mock_assess, mock_sub, mock_replace, mock_auto
    ):
        """Auto-scoring is skipped for IN_PROGRESS drafts."""
        from submissions.services import create_submission

        assignment = _mock_assignment()
        assignment_template = _mock_assessment(grading_mode=GradingMode.AUTO)
        new_sub = _mock_submission()

        mock_assign.objects.filter.return_value.first.return_value = assignment
        mock_assess.objects.filter.return_value.first.return_value = assignment_template
        mock_find.return_value = None
        mock_sub.objects.create.return_value = new_sub

        create_submission(10, {"studentId": 1}, SubmissionStatus.IN_PROGRESS)

        mock_auto.assert_not_called()

    @patch("submissions.services._auto_score_submission")
    @patch("submissions.services._replace_answers")
    @patch("submissions.services.Submission")
    @patch("submissions.services.AssignmentTemplate")
    @patch("submissions.services.Assignment")
    @patch("submissions.services._find_existing_submission")
    def test_no_auto_score_for_manual_mode(
        self, mock_find, mock_assign, mock_assess, mock_sub, mock_replace, mock_auto
    ):
        """Auto-scoring is skipped for MANUAL grading mode."""
        from submissions.services import create_submission

        assignment = _mock_assignment()
        assignment_template = _mock_assessment(grading_mode=GradingMode.MANUAL)
        new_sub = _mock_submission()

        mock_assign.objects.filter.return_value.first.return_value = assignment
        mock_assess.objects.filter.return_value.first.return_value = assignment_template
        mock_find.return_value = None
        mock_sub.objects.create.return_value = new_sub

        create_submission(10, {"studentId": 1}, SubmissionStatus.SUBMITTED)

        mock_auto.assert_not_called()

    @patch("submissions.services._auto_score_submission")
    @patch("submissions.services._replace_answers")
    @patch("submissions.services.Submission")
    @patch("submissions.services.AssignmentTemplate")
    @patch("submissions.services.Assignment")
    @patch("submissions.services._find_existing_submission")
    @patch("submissions.services.timezone")
    def test_sets_submitted_at_when_not_in_progress(
        self, mock_tz, mock_find, mock_assign, mock_assess, mock_sub, _replace, _auto
    ):
        """submitted_at is auto-set to now() when status is not IN_PROGRESS."""
        from submissions.services import create_submission

        fake_now = timezone.now()
        mock_tz.now.return_value = fake_now

        assignment = _mock_assignment()
        assignment_template = _mock_assessment(grading_mode=GradingMode.MANUAL)
        new_sub = _mock_submission()

        mock_assign.objects.filter.return_value.first.return_value = assignment
        mock_assess.objects.filter.return_value.first.return_value = assignment_template
        mock_find.return_value = None
        mock_sub.objects.create.return_value = new_sub

        create_submission(10, {"studentId": 1}, SubmissionStatus.SUBMITTED)

        create_call = mock_sub.objects.create.call_args
        assert create_call.kwargs["submitted_at"] == fake_now


# ============================================================================
# get_submission
# ============================================================================


class TestGetSubmission:
    """Tests for get_submission lookup."""

    @patch("submissions.services.Submission")
    def test_returns_submission(self, mock_model):
        """Found submission is returned directly."""
        from submissions.services import get_submission

        sub = _mock_submission(id=5)
        mock_model.objects.filter.return_value.first.return_value = sub

        assert get_submission(5) is sub

    @patch("submissions.services.Submission")
    def test_raises_when_not_found(self, mock_model):
        """ValueError raised when no submission with the given ID exists."""
        from submissions.services import get_submission

        mock_model.objects.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Submission not found"):
            get_submission(999)


# ============================================================================
# get_by_assignment / get_by_student / get_by_teacher
# ============================================================================


class TestGetByFilters:
    """Tests for simple filter-based retrieval functions."""

    @patch("submissions.services.Submission")
    def test_get_by_assignment(self, mock_model):
        """Returns list of submissions for a given assignment."""
        from submissions.services import get_by_assignment

        subs = [_mock_submission(id=1), _mock_submission(id=2)]
        qs = MagicMock()
        qs.select_related.return_value = subs
        mock_model.objects.filter.return_value = qs

        result = get_by_assignment(10)
        assert len(result) == 2

    @patch("submissions.services.Submission")
    def test_get_by_student(self, mock_model):
        """Returns list of submissions for a given student."""
        from submissions.services import get_by_student

        subs = [_mock_submission(id=3)]
        qs = MagicMock()
        qs.select_related.return_value = subs
        mock_model.objects.filter.return_value = qs

        result = get_by_student(100)
        assert len(result) == 1



# ============================================================================
# get_by_student_and_assignment
# ============================================================================


class TestGetByStudentAndAssignment:
    """Tests for cross-filter retrieval."""

    @patch("submissions.services.Submission")
    def test_returns_matching_submission(self, mock_model):
        """Returns the submission for student+assignment combination."""
        from submissions.services import get_by_student_and_assignment

        sub = _mock_submission(id=8)
        mock_model.objects.filter.return_value.first.return_value = sub

        assert get_by_student_and_assignment(100, 10) is sub

    @patch("submissions.services.Submission")
    def test_raises_when_not_found(self, mock_model):
        """ValueError raised when no submission matches."""
        from submissions.services import get_by_student_and_assignment

        mock_model.objects.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Submission not found"):
            get_by_student_and_assignment(100, 10)


# ============================================================================
# list_mine
# ============================================================================


class TestListMe:
    """Tests for the list_me service (user dashboard)."""

    @patch("submissions.services.Submission")
    def test_combines_student_and_teacher_subs(self, mock_model):
        """Q-based filter returns ordered queryset for a user."""
        from submissions.services import list_me

        s1 = _mock_submission(id=1, assignment_id=10, status=SubmissionStatus.SUBMITTED, submitted_at=timezone.now())
        s2 = _mock_submission(id=2, assignment_id=11, status=SubmissionStatus.GRADED, submitted_at=timezone.now())

        # list_me chains .filter(Q(...)).order_by(...) — mock the chain.
        mock_qs = MagicMock()
        mock_qs.order_by.return_value = mock_qs
        mock_qs.__iter__ = MagicMock(return_value=iter([s1, s2]))
        mock_qs.__len__ = MagicMock(return_value=2)
        mock_model.objects.filter.return_value = mock_qs

        result = list_me(100, None)

        # Result is a (mock) queryset, verify order_by was called
        mock_qs.order_by.assert_called_once()

    @patch("submissions.services.Submission")
    def test_filters_by_status(self, mock_model):
        """When status param is provided, only matching submissions are returned."""
        from submissions.services import list_me

        # Chain: .filter(Q(...)).filter(status=...).order_by(...) — mock the chain.
        inner_qs = MagicMock()
        inner_qs.order_by.return_value = inner_qs
        mock_model.objects.filter.return_value.filter.return_value = inner_qs

        result = list_me(100, SubmissionStatus.GRADED)

        inner_qs.order_by.assert_called_once()

    @patch("submissions.services.Submission")
    def test_returns_empty_when_no_submissions(self, mock_model):
        """Returns empty queryset when user has no submissions."""
        from submissions.services import list_me

        mock_qs = MagicMock()
        mock_qs.order_by.return_value = mock_qs
        mock_qs.__iter__ = MagicMock(return_value=iter([]))
        mock_qs.__len__ = MagicMock(return_value=0)
        mock_model.objects.filter.return_value = mock_qs

        result = list_me(100, None)
        mock_qs.order_by.assert_called_once()


# ============================================================================
# edit_submission
# ============================================================================


class TestEditSubmission:
    """Tests for the edit_submission service function."""

    def test_raises_when_assignment_id_missing(self):
        """ValueError raised when payload has no assignmentId."""
        from submissions.services import edit_submission

        with pytest.raises(ValueError, match="assignmentId is required"):
            edit_submission({"studentId": 1})

    @patch("submissions.services._find_existing_submission")
    def test_raises_when_submission_not_found(self, mock_find):
        """ValueError raised when no existing submission is found."""
        from submissions.services import edit_submission

        mock_find.return_value = None

        with pytest.raises(ValueError, match="Submission not found"):
            edit_submission({"assignmentId": 10, "studentId": 1})

    @patch("submissions.services._auto_score_submission")
    @patch("submissions.services._replace_answers")
    @patch("submissions.services.AssignmentTemplate")
    @patch("submissions.services._find_existing_submission")
    def test_updates_fields_and_saves(self, mock_find, mock_assess, mock_replace, mock_auto):
        """Edit updates submitted_at, score, status and replaces answers."""
        from submissions.services import edit_submission

        sub = _mock_submission(status=SubmissionStatus.IN_PROGRESS)
        sub.assignment = _mock_assignment(assignment_template_id=20)
        mock_find.return_value = sub

        assignment_template = _mock_assessment(grading_mode=GradingMode.AUTO)
        mock_assess.objects.filter.return_value.first.return_value = assignment_template

        edit_submission({
            "assignmentId": 10,
            "studentId": 1,
            "status": SubmissionStatus.SUBMITTED,
            "answers": [{"questionId": 1, "type": "SHORT_ANSWER", "data": {"text": "hi"}}],
        })

        mock_replace.assert_called_once()
        mock_auto.assert_called_once_with(sub, assignment_template)
        sub.save.assert_called_once()

    @patch("submissions.services._auto_score_submission")
    @patch("submissions.services._replace_answers")
    @patch("submissions.services.AssignmentTemplate")
    @patch("submissions.services._find_existing_submission")
    def test_no_auto_score_for_manual(self, mock_find, mock_assess, _replace, mock_auto):
        """Edit does not auto-score when grading mode is MANUAL."""
        from submissions.services import edit_submission

        sub = _mock_submission(status=SubmissionStatus.IN_PROGRESS)
        sub.assignment = _mock_assignment(assignment_template_id=20)
        mock_find.return_value = sub

        assignment_template = _mock_assessment(grading_mode=GradingMode.MANUAL)
        mock_assess.objects.filter.return_value.first.return_value = assignment_template

        edit_submission({
            "assignmentId": 10,
            "studentId": 1,
            "status": SubmissionStatus.SUBMITTED,
        })

        mock_auto.assert_not_called()


# ============================================================================
# override_score
# ============================================================================


class TestOverrideScore:
    """Tests for the teacher score override function."""

    @patch("submissions.services.Submission")
    def test_raises_when_submission_not_found(self, mock_model):
        """ValueError raised when submission_id does not exist."""
        from submissions.services import override_score

        mock_model.objects.select_related.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Submission not found"):
            override_score(999, [10])

    @patch("submissions.services.Submission")
    def test_raises_when_scores_empty(self, mock_model):
        """ValueError raised when scores list is empty."""
        from submissions.services import override_score

        sub = _mock_submission()
        mock_model.objects.select_related.return_value.filter.return_value.first.return_value = sub

        with pytest.raises(ValueError, match="Override score request must include score values"):
            override_score(1, [])

    @patch("submissions.services.Answer")
    @patch("submissions.services.Submission")
    def test_raises_when_assessment_not_found(self, mock_sub_model, _answer):
        """ValueError raised when linked assignment_template does not exist."""
        from submissions.services import override_score

        sub = _mock_submission()
        sub.assignment = _mock_assignment(assignment_template_id=20)
        sub.assignment.assignment_template = None
        mock_sub_model.objects.select_related.return_value.filter.return_value.first.return_value = sub

        with pytest.raises(ValueError, match="AssignmentTemplate not found"):
            override_score(1, [10])

    @patch("submissions.services.Question")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Submission")
    def test_manual_mode_applies_scores_in_order(self, mock_sub_model, mock_answer_model, mock_question):
        """MANUAL mode applies scores[i] to answers[i] and sums total."""
        from submissions.services import override_score

        a1 = _mock_answer(answer_type=AnswerType.SHORT_ANSWER, question_id=1, score=None)
        a2 = _mock_answer(answer_type=AnswerType.SHORT_ANSWER, question_id=2, score=None)

        sub = _mock_submission(answers=[a1, a2])
        sub.assignment = _mock_assignment(assignment_template_id=20)
        assignment_template = _mock_assessment(grading_mode=GradingMode.MANUAL)
        assignment_template.scoring_policy = "STANDARD"
        sub.assignment.assignment_template = assignment_template
        mock_sub_model.objects.select_related.return_value.filter.return_value.first.return_value = sub

        # Mock Question max_points lookup — no cap (values_list returns empty)
        mock_question.objects.filter.return_value.values_list.return_value = [(1, 100.0), (2, 100.0)]

        result = override_score(1, [3.0, 7.0])

        assert a1.score == 3.0
        assert a2.score == 7.0
        assert result.score == 10.0
        assert result.status == SubmissionStatus.GRADED

    @patch("submissions.services.Question")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Submission")
    def test_manual_mode_bonus_points(self, mock_sub_model, mock_answer_model, mock_question):
        """Extra scores beyond answer count add the last score as bonus."""
        from submissions.services import override_score

        a1 = _mock_answer(answer_type=AnswerType.SHORT_ANSWER, question_id=1, score=None)

        sub = _mock_submission(answers=[a1])
        sub.assignment = _mock_assignment(assignment_template_id=20)
        assignment_template = _mock_assessment(grading_mode=GradingMode.MANUAL)
        assignment_template.scoring_policy = "STANDARD"
        sub.assignment.assignment_template = assignment_template
        mock_sub_model.objects.select_related.return_value.filter.return_value.first.return_value = sub

        mock_question.objects.filter.return_value.values_list.return_value = [(1, 100.0)]

        result = override_score(1, [5.0, 2.0])

        # a1.score = 5.0, total = 5.0 + 2.0 (bonus) = 7.0
        assert a1.score == 5.0
        assert result.score == 7.0

    @patch("submissions.services.Question")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Submission")
    def test_hybrid_mode_only_scores_short_answer(self, mock_sub_model, mock_answer_model, mock_question):
        """HYBRID mode only applies manual scores to SHORT_ANSWER questions."""
        from submissions.services import override_score

        a_mcq = _mock_answer(answer_type=AnswerType.MULTIPLE_CHOICE, question_id=1, score=3.0)
        a_sa = _mock_answer(answer_type=AnswerType.SHORT_ANSWER, question_id=2, score=None)

        sub = _mock_submission(answers=[a_mcq, a_sa])
        sub.assignment = _mock_assignment(assignment_template_id=20)
        assignment_template = _mock_assessment(grading_mode=GradingMode.HYBRID)
        assignment_template.scoring_policy = "STANDARD"
        sub.assignment.assignment_template = assignment_template
        mock_sub_model.objects.select_related.return_value.filter.return_value.first.return_value = sub

        mock_question.objects.filter.return_value.values_list.return_value = [(1, 100.0), (2, 100.0)]

        result = override_score(1, [8.0])

        # MCQ keeps its auto-score of 3.0, SA gets the manual 8.0
        assert a_sa.score == 8.0
        assert result.score == 11.0  # 3.0 + 8.0

    @patch("submissions.services.Question")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Submission")
    def test_hybrid_mode_bonus_points(self, mock_sub_model, mock_answer_model, mock_question):
        """HYBRID mode adds last score as bonus if extra scores remain."""
        from submissions.services import override_score

        a_sa = _mock_answer(answer_type=AnswerType.SHORT_ANSWER, question_id=1, score=None)

        sub = _mock_submission(answers=[a_sa])
        sub.assignment = _mock_assignment(assignment_template_id=20)
        assignment_template = _mock_assessment(grading_mode=GradingMode.HYBRID)
        assignment_template.scoring_policy = "STANDARD"
        sub.assignment.assignment_template = assignment_template
        mock_sub_model.objects.select_related.return_value.filter.return_value.first.return_value = sub

        mock_question.objects.filter.return_value.values_list.return_value = [(1, 100.0)]

        # Two scores for one SA -- second is bonus
        result = override_score(1, [5.0, 3.0])

        assert a_sa.score == 5.0
        # total = 5.0 (from answer) + 3.0 (bonus, scores[-1])
        assert result.score == 8.0

    @patch("submissions.services.Question")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Submission")
    def test_manual_mode_uses_question_order_not_raw_answer_order(
        self,
        mock_sub_model,
        mock_answer_model,
        mock_question,
    ):
        """Score payloads align with sorted question order, not arbitrary DB row order."""
        from submissions.services import override_score

        a_scale = _mock_answer(
            answer_type=AnswerType.NUMBER_SCALE,
            question_id=14,
            score=None,
            max_points=5.0,
        )
        a_mcq = _mock_answer(
            answer_type=AnswerType.MULTIPLE_CHOICE,
            question_id=13,
            score=None,
            max_points=2.0,
        )
        a_select_all = _mock_answer(
            answer_type=AnswerType.MULTIPLE_CHOICE,
            question_id=15,
            score=None,
            max_points=2.0,
        )

        sub = _mock_submission(answers=[a_scale, a_mcq, a_select_all])
        sub.assignment = _mock_assignment(assignment_template_id=20)
        assignment_template = _mock_assessment(grading_mode=GradingMode.MANUAL)
        assignment_template.scoring_policy = "STANDARD"
        sub.assignment.assignment_template = assignment_template
        mock_sub_model.objects.select_related.return_value.filter.return_value.first.return_value = sub

        mock_question.objects.filter.return_value.values_list.return_value = [
            (13, 2.0),
            (14, 5.0),
            (15, 2.0),
        ]

        result = override_score(1, [2.0, 5.0, 1.0])

        assert a_mcq.score == 2.0
        assert a_scale.score == 5.0
        assert a_select_all.score == 1.0
        assert result.score == 8.0

    @patch("submissions.services.Submission")
    def test_error_uses_relative_question_label(self, mock_sub_model):
        """Validation errors should refer to the question position, not the DB id."""
        from submissions.services import override_score

        answer = _mock_answer(
            answer_type=AnswerType.MULTIPLE_CHOICE,
            question_id=13,
            score=None,
            max_points=2.0,
        )
        answer.question.prompt = "Which classroom supports helped most?"

        sub = _mock_submission(answers=[answer])
        sub.assignment = _mock_assignment(assignment_template_id=20)
        assignment_template = _mock_assessment(grading_mode=GradingMode.MANUAL)
        assignment_template.scoring_policy = "STANDARD"
        sub.assignment.assignment_template = assignment_template
        mock_sub_model.objects.select_related.return_value.filter.return_value.first.return_value = sub

        with pytest.raises(ValueError, match=r"Question 1"):
            override_score(1, [5.0])


# ============================================================================
# _find_existing_submission
# ============================================================================


class TestFindExistingSubmission:
    """Tests for the private _find_existing_submission helper."""

    @patch("submissions.services.Submission")
    def test_find_by_student_id(self, mock_model):
        """Finds by assignment_id and student_id when student_id is set."""
        from submissions.services import _find_existing_submission

        sub = _mock_submission()
        mock_model.objects.filter.return_value.first.return_value = sub

        result = _find_existing_submission(10, student_id=100, teacher_id=None)

        assert result is sub
        mock_model.objects.filter.assert_called_with(assignment_id=10, student_id=100)

    @patch("submissions.services.Submission")
    def test_find_by_teacher_id(self, mock_model):
        """Finds by assignment_id and teacher_id when teacher_id is set."""
        from submissions.services import _find_existing_submission

        sub = _mock_submission()
        mock_model.objects.filter.return_value.first.return_value = sub

        result = _find_existing_submission(10, student_id=None, teacher_id=200)

        assert result is sub
        mock_model.objects.filter.assert_called_with(assignment_id=10, teacher_id=200)

    @patch("submissions.services.Submission")
    def test_returns_none_when_both_ids_none(self, mock_model):
        """Returns None when both student_id and teacher_id are None."""
        from submissions.services import _find_existing_submission

        result = _find_existing_submission(10, student_id=None, teacher_id=None)

        assert result is None
        mock_model.objects.filter.assert_not_called()


# ============================================================================
# _create_answer
# ============================================================================


class TestCreateAnswer:
    """Tests for the private _create_answer helper."""

    @patch("submissions.services.MultipleChoiceSelected")
    @patch("submissions.services.MultipleChoiceAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_raises_when_question_id_missing(self, mock_q, mock_a, _mc, _mcs):
        """ValueError raised when questionId is not in payload."""
        from submissions.services import _create_answer

        with pytest.raises(ValueError, match="Question ID is required"):
            _create_answer(_mock_submission(), {})

    @patch("submissions.services.MultipleChoiceSelected")
    @patch("submissions.services.MultipleChoiceAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_raises_when_question_not_found(self, mock_q, mock_a, _mc, _mcs):
        """ValueError raised when question with given ID does not exist."""
        from submissions.services import _create_answer

        mock_q.objects.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Question not found"):
            _create_answer(_mock_submission(), {"questionId": 999})

    @patch("submissions.services.MultipleChoiceSelected")
    @patch("submissions.services.MultipleChoiceAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_raises_when_answer_type_missing(self, mock_q, mock_a, _mc, _mcs):
        """ValueError raised when answer type is not in payload."""
        from submissions.services import _create_answer

        mock_q.objects.filter.return_value.first.return_value = _mock_question()

        with pytest.raises(ValueError, match="Answer type is required"):
            _create_answer(_mock_submission(), {"questionId": 1})

    @patch("submissions.services.MultipleChoiceSelected")
    @patch("submissions.services.MultipleChoiceAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_creates_multiple_choice_answer(self, mock_q, mock_a, mock_mc, mock_mcs):
        """MCQ answer creates a MultipleChoiceAnswer with selected indices."""
        from submissions.services import _create_answer

        mock_q.objects.filter.return_value.first.return_value = _mock_question(question_type="MULTIPLE_CHOICE")
        answer_obj = MagicMock()
        mock_a.objects.create.return_value = answer_obj
        mc_obj = MagicMock()
        mock_mc.objects.create.return_value = mc_obj

        payload = {
            "questionId": 1,
            "type": AnswerType.MULTIPLE_CHOICE,
            "data": {"selected": [0, 2]},
        }
        _create_answer(_mock_submission(), payload)

        mock_mc.objects.create.assert_called_once_with(answer=answer_obj)
        assert mock_mcs.objects.create.call_count == 2

    @patch("submissions.services.ShortAnswerAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_creates_short_answer(self, mock_q, mock_a, mock_sa):
        """Short answer creates a ShortAnswerAnswer with text."""
        from submissions.services import _create_answer

        mock_q.objects.filter.return_value.first.return_value = _mock_question()
        answer_obj = MagicMock()
        mock_a.objects.create.return_value = answer_obj

        payload = {
            "questionId": 1,
            "type": AnswerType.SHORT_ANSWER,
            "data": {"text": "My answer"},
        }
        _create_answer(_mock_submission(), payload)

        mock_sa.objects.create.assert_called_once_with(answer=answer_obj, text="My answer")

    @patch("submissions.services.NumberScaleAnswer")
    @patch("submissions.services.Answer")
    @patch("submissions.services.Question")
    def test_creates_number_scale_answer(self, mock_q, mock_a, mock_ns):
        """Number scale creates a NumberScaleAnswer with the value."""
        from submissions.services import _create_answer

        mock_q.objects.filter.return_value.first.return_value = _mock_question(question_type="NUMBER_SCALE")
        answer_obj = MagicMock()
        mock_a.objects.create.return_value = answer_obj

        payload = {
            "questionId": 1,
            "type": AnswerType.NUMBER_SCALE,
            "data": {"val": 7},
        }
        _create_answer(_mock_submission(), payload)

        mock_ns.objects.create.assert_called_once_with(answer=answer_obj, val=7)



# ============================================================================
# _auto_score_submission
# ============================================================================


class TestAutoScoreSubmission:
    """Tests for the internal auto-scoring logic."""

    def test_skips_non_gradable_questions(self):
        """Questions with auto_gradable=False are not scored."""
        from submissions.services import _auto_score_submission

        q = _mock_question(auto_gradable=False)
        a = _mock_answer(answer_type=AnswerType.MULTIPLE_CHOICE, score=None)
        a.question = q

        sub = _mock_submission(answers=[a])
        assignment_template = _mock_assessment(grading_mode=GradingMode.AUTO)

        _auto_score_submission(sub, assignment_template)

        assert sub.score == 0.0

    def test_sets_graded_status_for_auto_mode(self):
        """AUTO mode sets status to GRADED and sets submitted_at if None."""
        from submissions.services import _auto_score_submission

        sub = _mock_submission(answers=[], submitted_at=None)
        assignment_template = _mock_assessment(grading_mode=GradingMode.AUTO)

        _auto_score_submission(sub, assignment_template)

        assert sub.status == SubmissionStatus.GRADED
        assert sub.submitted_at is not None

    def test_does_not_set_graded_for_hybrid_mode(self):
        """HYBRID mode does not change status to GRADED (needs manual step)."""
        from submissions.services import _auto_score_submission

        sub = _mock_submission(answers=[], status=SubmissionStatus.SUBMITTED)
        assignment_template = _mock_assessment(grading_mode=GradingMode.HYBRID)

        _auto_score_submission(sub, assignment_template)

        assert sub.status == SubmissionStatus.SUBMITTED


# ============================================================================
# _auto_score_mcq
# ============================================================================


class TestAutoScoreMcq:
    """Tests for MCQ auto-scoring logic."""

    def test_scores_selected_choices(self):
        """Correct score is the sum of points for selected choices."""
        from submissions.services import _auto_score_mcq

        q = _mock_question(auto_gradable=True, max_points=10.0)
        choice_a = SimpleNamespace(points=0)
        choice_b = SimpleNamespace(points=5)
        choice_c = SimpleNamespace(points=3)
        q.mcq_choices.all.return_value = [choice_a, choice_b, choice_c]

        ans = _mock_answer(answer_type=AnswerType.MULTIPLE_CHOICE, score=None)
        mc = MagicMock()
        mc.selected.all.return_value = [SimpleNamespace(choice_index=1), SimpleNamespace(choice_index=2)]
        ans.multiple_choice = mc

        total = _auto_score_mcq(ans, q)

        assert total == 8.0  # 5 + 3
        assert ans.score == 8.0

    def test_skips_out_of_range_indices(self):
        """Indices beyond choice count or negative are silently skipped."""
        from submissions.services import _auto_score_mcq

        q = _mock_question()
        choice_a = SimpleNamespace(points=5)
        q.mcq_choices.all.return_value = [choice_a]

        ans = _mock_answer(answer_type=AnswerType.MULTIPLE_CHOICE)
        mc = MagicMock()
        mc.selected.all.return_value = [
            SimpleNamespace(choice_index=-1),
            SimpleNamespace(choice_index=0),
            SimpleNamespace(choice_index=5),
            SimpleNamespace(choice_index=None),
        ]
        ans.multiple_choice = mc

        total = _auto_score_mcq(ans, q)

        # Only index 0 is valid, so score = 5
        assert total == 5.0

    def test_no_selections_yields_zero(self):
        """Empty selection list produces a score of 0."""
        from submissions.services import _auto_score_mcq

        q = _mock_question()
        q.mcq_choices.all.return_value = [SimpleNamespace(points=5)]

        ans = _mock_answer(answer_type=AnswerType.MULTIPLE_CHOICE)
        mc = MagicMock()
        mc.selected.all.return_value = []
        ans.multiple_choice = mc

        total = _auto_score_mcq(ans, q)
        assert total == 0.0

    def test_caps_score_at_max_points(self):
        """Select-all totals should never exceed the question max_points."""
        from submissions.services import _auto_score_mcq

        q = _mock_question(max_points=2.0)
        q.mcq_choices.all.return_value = [
            SimpleNamespace(points=1),
            SimpleNamespace(points=1),
            SimpleNamespace(points=1),
        ]

        ans = _mock_answer(answer_type=AnswerType.MULTIPLE_CHOICE)
        mc = MagicMock()
        mc.selected.all.return_value = [
            SimpleNamespace(choice_index=0),
            SimpleNamespace(choice_index=1),
            SimpleNamespace(choice_index=2),
        ]
        ans.multiple_choice = mc

        total = _auto_score_mcq(ans, q)

        assert total == 2.0
        assert ans.score == 2.0


# ============================================================================
# _auto_score_number_scale
# ============================================================================


class TestAutoScoreNumberScale:
    """Tests for number scale auto-scoring logic."""

    def test_exact_match_gives_full_points(self):
        """Score equals max_points when answer matches the target."""
        from submissions.services import _auto_score_number_scale

        q = _mock_question(max_points=10.0)
        q.number_scale = SimpleNamespace(target=7)

        ans = _mock_answer(answer_type=AnswerType.NUMBER_SCALE)
        ans.number_scale = SimpleNamespace(val=7)

        total = _auto_score_number_scale(ans, q)

        assert total == 10.0
        assert ans.score == 10.0

    def test_mismatch_gives_zero(self):
        """Score is 0 when answer does not match the target."""
        from submissions.services import _auto_score_number_scale

        q = _mock_question(max_points=10.0)
        q.number_scale = SimpleNamespace(target=7)

        ans = _mock_answer(answer_type=AnswerType.NUMBER_SCALE)
        ans.number_scale = SimpleNamespace(val=5)

        total = _auto_score_number_scale(ans, q)

        assert total == 0.0

    def test_no_target_returns_zero(self):
        """Score is 0 when the question has no target defined."""
        from submissions.services import _auto_score_number_scale

        q = _mock_question(max_points=10.0)
        q.number_scale = SimpleNamespace(target=None)

        ans = _mock_answer(answer_type=AnswerType.NUMBER_SCALE)
        ans.number_scale = SimpleNamespace(val=5)

        total = _auto_score_number_scale(ans, q)

        assert total == 0.0
