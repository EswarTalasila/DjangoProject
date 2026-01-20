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
    NUMBER_SCALE: {"value": 4}
    MOOD_METER: {"row": 1, "col": 2}
"""

from rest_framework import serializers


class AnswerSerializer(serializers.Serializer):
    """
    Validates answer payloads within a submission.

    The 'data' field contains the actual response, with format depending
    on the answer type. The service layer validates and processes this.

    Fields:
        questionId: ID of the question being answered
        type: Answer type (must match question type)
        data: Type-specific response data (selected choices, text, etc.)
        score: Points awarded (set by grading, null until graded)
    """

    questionId = serializers.IntegerField()
    type = serializers.ChoiceField(
        choices=["MULTIPLE_CHOICE", "SHORT_ANSWER", "NUMBER_SCALE", "MOOD_METER"]
    )
    data = serializers.DictField()  # type: ignore[assignment]
    score = serializers.FloatField(required=False, allow_null=True)


class SubmissionSerializer(serializers.Serializer):
    """
    Validates submission update payloads.

    Submissions are pre-created when assignments are made. Students
    cannot create submissions - they can only update existing ones
    by adding/modifying answers.

    Fields:
        id: Submission ID (for updates)
        assignmentId: The assignment this submission is for
        studentId: Student user ID (for COURSE assignments)
        teacherId: Teacher user ID (for TEACHER assignments)
        submittedAt: Timestamp of submission (set when status→SUBMITTED)
        score: Total score (set after grading)
        status: Current lifecycle state
        answers: List of AnswerSerializer objects

    Status Values:
        NOT_STARTED: Submission created but no answers yet
        IN_PROGRESS: Student has started answering
        SUBMITTED: Student has submitted for grading
        GRADED: Teacher has reviewed and scored
    """

    id = serializers.IntegerField(required=False)
    assignmentId = serializers.IntegerField()
    studentId = serializers.IntegerField(required=False, allow_null=True)
    teacherId = serializers.IntegerField(required=False, allow_null=True)
    submittedAt = serializers.DateTimeField(required=False, allow_null=True)
    score = serializers.FloatField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=["NOT_STARTED", "IN_PROGRESS", "SUBMITTED", "GRADED"])
    answers = AnswerSerializer(many=True, required=False)
