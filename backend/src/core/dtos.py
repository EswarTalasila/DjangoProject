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
    groupId: int | None = None
    rubricId: int | None = None
    gradingStrategy: str = "AUTO"


class QuestionGroupDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    rubricId: int | None = None
    orderIndex: int = 0


class AssessmentDTO(BaseModel):
    """Full assessment with all questions."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: str | None
    gradingMode: str
    scoringPolicy: str = "STANDARD"
    questions: list[QuestionDTO]
    questionGroups: list[QuestionGroupDTO] = []


# =============================================================================
# Rubric DTOs
# =============================================================================


class RubricLevelDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    points: float
    description: str
    orderIndex: int


class RubricCriterionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    orderIndex: int
    weight: float
    levels: list[RubricLevelDTO]


class RubricDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: str
    createdBy: int
    createdAt: datetime
    updatedAt: datetime
    criteria: list[RubricCriterionDTO]


# =============================================================================
# Assignment DTOs
# =============================================================================


class AssignmentDTO(BaseModel):
    """Assignment linking assessment to audience."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    assessmentId: int
    assessmentTitle: str | None = None
    audienceType: str
    courseId: int | None
    targetTeacherId: int | None
    openAt: datetime | None
    dueAt: datetime | None
    status: str = "ACTIVE"


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


class SubmissionImageDTO(BaseModel):
    """Image metadata for submission image responses (FR-15)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    originalFilename: str
    mimeType: str
    sizeBytes: int
    uploadedByUserId: int | None
    status: str
    createdAt: datetime


