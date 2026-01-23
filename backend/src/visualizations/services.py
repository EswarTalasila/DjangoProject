"""
Visualization data helpers.

This module provides data aggregation for the dashboard visualization views.
It queries submission data with flexible filtering and returns enriched DTOs
that include course and assessment metadata for display purposes.

The visualization endpoint is used by teachers and admins to view aggregated
student performance data across courses, assessments, and categories.
"""

from assessments.models import Assessment, GradingMode
from core.dtos import VisualizationSubmissionDTO
from submissions.models import Submission, SubmissionStatus
from submissions.services import answer_to_dto


def _get_mood_meter_assessment_id() -> int | None:
    """Get the ID of the MOOD_METER assessment if one exists."""
    return (
        Assessment.objects.filter(grading_mode=GradingMode.MOOD_METER)
        .values_list("id", flat=True)
        .first()
    )


def get_visualization_data(filters: dict, request_user) -> list[VisualizationSubmissionDTO]:
    """
    Query submission data for dashboard visualizations.

    Supports filtering by:
    - studentId: Submissions for a specific student
    - courseId: Submissions for a specific course
    - category: Submissions for assessments in a category
    - assessmentId: Submissions for a specific assessment

    By default, excludes MOOD_METER submissions unless specifically filtered
    to that assessment, since mood meter data is typically visualized separately.

    Args:
        filters: Dict with optional studentId, courseId, category, assessmentId
        request_user: The user requesting data (for future permission scoping)

    Returns:
        List of VisualizationSubmissionDTOs with submission and context data
    """
    student_id = filters.get("studentId")
    course_id = filters.get("courseId")
    category = filters.get("category")
    assessment_id = filters.get("assessmentId")

    submissions = Submission.objects.filter(status=SubmissionStatus.GRADED)

    if student_id is not None:
        submissions = submissions.filter(student_id=student_id)
    if course_id is not None:
        submissions = submissions.filter(assignment__course_id=course_id)
    if category:
        submissions = submissions.filter(assignment__assessment__category=category)
    if assessment_id is not None:
        submissions = submissions.filter(assignment__assessment_id=assessment_id)

    # Exclude MOOD_METER submissions from general queries because they're
    # typically displayed in a separate heatmap visualization, not mixed
    # with regular assessment data. Only include them if specifically
    # filtering for the mood meter assessment.
    mood_meter_id = _get_mood_meter_assessment_id()
    if (
        mood_meter_id
        and (
            student_id is not None or course_id is not None or category or assessment_id is not None
        )
        and (assessment_id is None or assessment_id != mood_meter_id)
    ):
        submissions = submissions.exclude(assignment__assessment_id=mood_meter_id)

    submissions = submissions.select_related("assignment", "assignment__assessment")
    submissions = submissions.order_by("-submitted_at")

    return [submission_to_visualization(sub) for sub in submissions]


def submission_to_visualization(submission: Submission) -> VisualizationSubmissionDTO:
    """
    Convert a Submission to an enriched DTO for visualization.

    Includes context data from the related assignment, assessment, and course
    that is needed for dashboard display but not included in the basic
    submission DTO.

    Returns:
        VisualizationSubmissionDTO with standard submission fields plus courseId,
        courseName, assessmentTitle, and assessmentCategory
    """
    assignment = submission.assignment
    assessment = assignment.assessment if assignment else None
    course_id = assignment.course_id if assignment else None
    course_name = assignment.course.name if assignment and assignment.course else None

    return VisualizationSubmissionDTO(
        id=submission.id,
        assignmentId=submission.assignment_id,
        studentId=submission.student_id,
        teacherId=submission.teacher_id,
        submittedAt=submission.submitted_at,
        score=submission.score,
        status=submission.status,
        answers=[answer_to_dto(answer) for answer in submission.answers.all()],
        courseId=course_id,
        courseName=course_name,
        assessmentTitle=assessment.title if assessment else None,
        assessmentCategory=assessment.category if assessment else None,
    )
