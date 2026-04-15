"""
Assignment domain helpers — re-exported from sub-modules.
"""

from ._mutations import (
    ConflictError,
    ForbiddenError,
    _create_submissions_for_course,
    archive_assignment,
    create_assignment,
    purge_assignment,
    restore_assignment,
    update_assignment,
)
from ._archive_exports import (
    assignment_archive_artifact_to_dict,
    cleanup_assignment_archive_artifacts,
    generate_assignment_archive_artifact,
    get_assignment_archive_artifact,
)
from ._content import (
    add_assignment_question,
    add_assignment_teacher_criterion,
    assignment_content_to_dto,
    assignment_has_progressed_submissions,
    assignment_question_to_dto,
    get_assignment_with_content,
    list_reusable_question_images,
    provision_submission_answers,
    snapshot_assignment_content,
)
from ._queries import (
    assignment_to_dto,
    get_assignment,
    list_by_course,
    list_for_user,
)

__all__ = [
    "ConflictError",
    "ForbiddenError",
    "_create_submissions_for_course",
    "add_assignment_question",
    "add_assignment_teacher_criterion",
    "assignment_archive_artifact_to_dict",
    "assignment_content_to_dto",
    "assignment_has_progressed_submissions",
    "assignment_question_to_dto",
    "archive_assignment",
    "assignment_to_dto",
    "cleanup_assignment_archive_artifacts",
    "create_assignment",
    "generate_assignment_archive_artifact",
    "get_assignment",
    "get_assignment_archive_artifact",
    "get_assignment_with_content",
    "list_reusable_question_images",
    "list_by_course",
    "list_for_user",
    "provision_submission_answers",
    "purge_assignment",
    "restore_assignment",
    "snapshot_assignment_content",
    "update_assignment",
]
