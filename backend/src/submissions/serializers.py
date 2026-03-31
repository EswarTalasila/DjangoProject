"""
Submission serializers.

This module provides DRF serializers for student submission management.
Submissions contain answers to questions from the assigned assessment.

Serializer Hierarchy:
    SubmissionSerializer
        └── AnswerSerializer (many=True)
            └── data (DictField with type-specific response data)

The 'data' field in AnswerSerializer contains the actual response:
    MULTIPLE_CHOICE: {"selected": [0, 2]}  (indices of selected choices)
    SHORT_ANSWER: {"text": "answer"}
    NUMBER_SCALE: {"val": 4}
"""

from rest_framework import serializers

# Required keys per answer type for structural validation of the data dict.
_REQUIRED_KEYS: dict[str, set[str]] = {
    "MULTIPLE_CHOICE": {"selected"},
    "SHORT_ANSWER": {"text"},
    "NUMBER_SCALE": {"val"},
}


class AnswerSerializer(serializers.Serializer):
    """
    Validates answer payloads within a submission.

    The 'data' field contains the actual response, with format depending
    on the answer type. The service layer validates type matching against
    the assessment question, but this serializer enforces structural
    requirements (e.g. MULTIPLE_CHOICE data must contain 'selected').

    Fields:
        questionId: ID of the question being answered
        type: Answer type (must match question type)
        data: Type-specific response data (selected choices, text, etc.)
        score: Points awarded (set by grading, read-only on input)
    """

    questionId = serializers.IntegerField()
    type = serializers.ChoiceField(choices=["MULTIPLE_CHOICE", "SHORT_ANSWER", "NUMBER_SCALE"])
    data = serializers.DictField()  # type: ignore[assignment]
    score = serializers.FloatField(required=False, allow_null=True, read_only=True)

    def validate(self, attrs):
        """Check that data dict contains the required keys for the answer type."""
        answer_type = attrs.get("type")
        data = attrs.get("data", {})
        required = _REQUIRED_KEYS.get(answer_type, set())
        missing = required - set(data.keys())
        if missing:
            raise serializers.ValidationError(
                {"data": f"Missing required key(s) for {answer_type}: {', '.join(sorted(missing))}"}
            )
        return attrs


class SubmissionSerializer(serializers.Serializer):
    """
    Validates submission input payloads.

    Submissions are pre-created when assignments are made. Students
    cannot create submissions - they can only update existing ones
    by adding/modifying answers.

    Fields:
        id: Submission ID (for updates)
        assignmentId: The assignment this submission is for
        studentId: Student user ID (for COURSE assignments)
        teacherId: Teacher user ID (for TEACHER assignments)
        submittedAt: Timestamp of submission (set when status->SUBMITTED, read-only)
        score: Total score (set after grading, read-only)
        status: Current lifecycle state (service-controlled, read-only)
        answers: List of AnswerSerializer objects

    Note: status, submittedAt, and score are read-only because the service
    layer controls lifecycle transitions. They are accepted on input for
    backward compatibility but ignored by the view layer.
    """

    id = serializers.IntegerField(required=False)
    assignmentId = serializers.IntegerField()
    studentId = serializers.IntegerField(required=False, allow_null=True)
    teacherId = serializers.IntegerField(required=False, allow_null=True)
    submittedAt = serializers.DateTimeField(required=False, allow_null=True, read_only=True)
    score = serializers.FloatField(required=False, allow_null=True, read_only=True)
    status = serializers.ChoiceField(
        choices=["NOT_STARTED", "IN_PROGRESS", "SUBMITTED", "GRADED"],
        required=False,
        read_only=True,
    )
    answers = AnswerSerializer(many=True, required=False)
