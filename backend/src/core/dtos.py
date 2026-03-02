"""
Pydantic DTOs for type-safe internal data transfer.

This module provides typed data transfer objects for all API responses.
Each DTO corresponds to a service function's return type and ensures
type safety, IDE autocomplete, and runtime validation.

Usage:
    from core.dtos import CourseDTO, AssessmentDTO

    def course_to_dto(course: Course) -> CourseDTO:
        return CourseDTO(id=course.id, name=course.name, ...)
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

# =============================================================================
# Course DTOs
# =============================================================================


class EnrollmentStudentDTO(BaseModel):
    """Student information from an enrollment record."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None
    name: str | None
    username: str | None
    role: str
    consent: bool
    courseId: int
    enrolledAt: datetime | None


class CourseDTO(BaseModel):
    """Full course representation with enrolled students."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    students: list[EnrollmentStudentDTO]
    studentCount: int
    assignmentIds: list[int]
    teacherId: int | None
    teacherName: str | None
    createdAt: datetime | None


# =============================================================================
# Assessment DTOs
# =============================================================================


class ChoiceDTO(BaseModel):
    """A single choice in a multiple choice question."""

    prompt: str
    score: int


class QuestionDTO(BaseModel):
    """Question representation with type-specific data."""

    model_config = ConfigDict(from_attributes=True)

    questionId: int
    id: int
    type: str
    prompt: str
    maxPoints: float
    autoGradable: bool
    graded: bool
    data: dict[str, Any] | None = None
    selectAll: bool | None = None
    min: int | None = None
    max: int | None = None


class AssessmentDTO(BaseModel):
    """Full assessment with all questions."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: str | None
    gradingMode: str
    questions: list[QuestionDTO]
    rubricId: int | None
    rubricAssessmentIds: list[int]


# =============================================================================
# Assignment DTOs
# =============================================================================


class AssignmentDTO(BaseModel):
    """Assignment linking assessment to audience."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    assessmentId: int
    audienceType: str
    courseId: int | None
    targetTeacherId: int | None
    openAt: datetime | None
    dueAt: datetime | None


# =============================================================================
# Submission DTOs
# =============================================================================


class AnswerDTO(BaseModel):
    """Answer with type-specific data."""

    model_config = ConfigDict(from_attributes=True)

    questionId: int
    type: str
    data: dict[str, Any]
    score: float | None


class SubmissionDTO(BaseModel):
    """Full submission with all answers."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    assignmentId: int
    studentId: int | None
    teacherId: int | None
    submittedAt: datetime | None
    score: float | None
    status: str
    answers: list[AnswerDTO]


class SubmissionCompactDTO(BaseModel):
    """Compact submission for list views (no answers)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    assignmentId: int
    submittedAt: datetime | None
    score: float | None
    status: str


# =============================================================================
# Visualization DTOs
# =============================================================================


class VisualizationSubmissionDTO(BaseModel):
    """Submission data for visualization dashboards with context."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    assignmentId: int
    studentId: int | None
    teacherId: int | None
    submittedAt: datetime | None
    score: float | None
    status: str
    answers: list[AnswerDTO]
    courseId: int | None
    courseName: str | None
    assessmentTitle: str | None
    assessmentCategory: str | None
