"""Archived assignment bundle generation and download helpers."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import Role, SudoPermission
from assignment_templates.image_services import parse_question_image
from core.permissions import has_role, has_sudo_permission
from core.media.storage import get_storage_backend
from submissions.models import AnswerType, SubmissionStatus

from ..models import Assignment, AssignmentArchiveArtifact, AssignmentStatus
from ._content import assignment_content_to_dto, snapshot_assignment_content
from ._mutations import ConflictError
from ._queries import assignment_to_dto

logger = logging.getLogger(__name__)


def assignment_archive_artifact_to_dict(artifact: AssignmentArchiveArtifact) -> dict:
    """Serialize archive artifact metadata for API responses."""
    return {
        "id": artifact.id,
        "assignmentId": artifact.assignment_id,
        "identifiable": artifact.identifiable,
        "filename": artifact.filename,
        "sizeBytes": artifact.size_bytes,
        "sha256Hash": artifact.sha256_hash,
        "generatedAt": artifact.generated_at.isoformat() if artifact.generated_at else None,
        "generatedByUserId": artifact.generated_by_id,
        "manifest": artifact.manifest,
    }


def get_assignment_archive_artifact(
    assignment: Assignment,
    request_user,
    *,
    identifiable: bool | None = None,
) -> AssignmentArchiveArtifact | None:
    """Return archive metadata for the permitted variant."""
    resolved_identifiable = _resolve_bundle_variant(request_user, identifiable)
    _ensure_bundle_access(request_user, assignment)
    return AssignmentArchiveArtifact.objects.filter(
        assignment=assignment,
        identifiable=resolved_identifiable,
    ).first()


@transaction.atomic
def generate_assignment_archive_artifact(
    assignment: Assignment,
    request_user,
    *,
    identifiable: bool | None = None,
) -> AssignmentArchiveArtifact:
    """Generate or replace an archived assignment ZIP artifact."""
    _ensure_bundle_access(request_user, assignment)
    if assignment.status != AssignmentStatus.ARCHIVED:
        raise ConflictError("Archive bundles are only available for archived assignments.")

    resolved_identifiable = _resolve_bundle_variant(request_user, identifiable)
    filename = _build_bundle_filename(assignment, resolved_identifiable)
    bundle_bytes, manifest = _build_bundle_bytes(
        assignment,
        request_user=request_user,
        identifiable=resolved_identifiable,
    )
    bundle_dir = Path(settings.ARTIFACT_ROOT) / "assignments"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    file_path = bundle_dir / filename

    existing = AssignmentArchiveArtifact.objects.filter(
        assignment=assignment,
        identifiable=resolved_identifiable,
    ).first()
    if existing is not None:
        _delete_artifact_file(existing.file_path)

    file_path.write_bytes(bundle_bytes)
    sha256_hash = hashlib.sha256(bundle_bytes).hexdigest()

    artifact, _ = AssignmentArchiveArtifact.objects.update_or_create(
        assignment=assignment,
        identifiable=resolved_identifiable,
        defaults={
            "generated_by": request_user,
            "filename": filename,
            "file_path": str(file_path),
            "size_bytes": len(bundle_bytes),
            "sha256_hash": sha256_hash,
            "manifest": manifest,
        },
    )
    return artifact


def cleanup_assignment_archive_artifacts(assignment: Assignment) -> None:
    """Delete all archive artifacts and files for an assignment."""
    artifacts = list(AssignmentArchiveArtifact.objects.filter(assignment=assignment))
    for artifact in artifacts:
        _delete_artifact_file(artifact.file_path)
    AssignmentArchiveArtifact.objects.filter(assignment=assignment).delete()


def _ensure_bundle_access(request_user, assignment: Assignment) -> None:
    """Validate that the caller can generate or download a bundle."""
    if request_user.is_staff:
        return
    if has_role(request_user, Role.TEACHER):
        if assignment.created_by_id == request_user.id:
            return
        raise PermissionError("Only the assignment creator or an admin can access this bundle.")
    if has_role(request_user, Role.RESEARCHER):
        return
    raise PermissionError("Only teachers, researchers, or admins can access archive bundles.")


def _resolve_bundle_variant(request_user, identifiable: bool | None) -> bool:
    """Resolve whether the bundle should include identifiable data."""
    if request_user.is_staff or has_role(request_user, Role.TEACHER):
        return True
    if not has_role(request_user, Role.RESEARCHER):
        raise PermissionError("Only researchers can request anonymized archive bundles.")
    if identifiable:
        if not has_sudo_permission(request_user, SudoPermission.EXPORT_IDENTIFIABLE):
            raise PermissionError("EXPORT_IDENTIFIABLE permission required.")
        return True
    return False


def _build_bundle_filename(assignment: Assignment, identifiable: bool) -> str:
    """Build a human-readable ZIP filename."""
    template_slug = slugify(assignment.assignment_template.title) or f"template-{assignment.assignment_template_id}"
    assignment_slug = slugify(assignment.title or assignment.assignment_template.title) or f"assignment-{assignment.id}"
    suffix = "identified" if identifiable else "anonymized"
    return f"{template_slug}--{assignment_slug}--{suffix}.zip"


def _build_bundle_root(assignment: Assignment) -> str:
    """Build a human-readable ZIP root directory."""
    template_payload = _get_template_snapshot_payload(assignment)
    template_title = template_payload.get("title") or assignment.assignment_template.title
    template_slug = slugify(template_title) or f"template-{assignment.assignment_template_id}"
    assignment_slug = slugify(assignment.title or template_title) or f"assignment-{assignment.id}"
    return (
        f"template-{template_slug}-{assignment.assignment_template_id}/"
        f"assignment-{assignment_slug}-{assignment.id}"
    )


def _build_bundle_bytes(
    assignment: Assignment,
    *,
    request_user,
    identifiable: bool,
) -> tuple[bytes, dict]:
    """Construct the ZIP bytes and manifest for an assignment bundle."""
    assignment = _load_assignment_for_bundle(assignment.id)
    if not assignment.template_snapshot:
        snapshot_assignment_content(
            assignment,
            assignment.assignment_template,
            creator_user_id=assignment.created_by_id,
        )
        assignment = _load_assignment_for_bundle(assignment.id)
    participant_labels = _build_participant_labels(assignment)
    template_dto = _get_template_snapshot_payload(assignment)
    content_dto = assignment_content_to_dto(assignment).model_dump(mode="json")
    assignment_dto = assignment_to_dto(assignment).model_dump(mode="json")
    manifest = _build_manifest(assignment, request_user, identifiable, participant_labels)
    root = _build_bundle_root(assignment)
    submissions = list(assignment.submissions.all())

    zip_buffer = io.BytesIO()
    with ZipFile(zip_buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(f"{root}/manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        archive.writestr(
            f"{root}/template/template.json",
            json.dumps(template_dto, indent=2, sort_keys=True),
        )
        archive.writestr(
            f"{root}/assignment/content.json",
            json.dumps(content_dto, indent=2, sort_keys=True),
        )
        archive.writestr(
            f"{root}/assignment/assignment.json",
            json.dumps(assignment_dto, indent=2, sort_keys=True),
        )
        archive.writestr(
            f"{root}/assignment/course.json",
            json.dumps(_serialize_course(assignment), indent=2, sort_keys=True),
        )
        archive.writestr(
            f"{root}/assignment/submissions.csv",
            _render_submission_csv(submissions, identifiable, participant_labels),
        )

        rubric_payloads = _serialize_rubrics(assignment)
        for relative_path, payload in rubric_payloads.items():
            archive.writestr(relative_path.replace("{root}", root), json.dumps(payload, indent=2, sort_keys=True))

        _write_question_images(archive, assignment, root)
        _write_submission_payloads(
            archive,
            submissions,
            root,
            identifiable=identifiable,
            participant_labels=participant_labels,
        )

    return zip_buffer.getvalue(), manifest


def _load_assignment_for_bundle(assignment_id: int) -> Assignment:
    """Refetch assignment with the relations needed to build the archive bundle."""
    from assignment_templates.models import AssignmentTemplateQuestionGroup
    from submissions.models import SubmissionImage

    return (
        Assignment.objects.select_related(
            "assignment_template",
            "assignment_template__rubric",
            "course",
            "created_by",
        )
        .prefetch_related(
            "assignment_template__question_groups",
            "assignment_template__question_groups__rubric",
            "assignment_template__questions__mcq_choices",
            "assignment_template__questions__multiple_choice",
            "assignment_template__questions__short_answer",
            "assignment_template__questions__number_scale",
            "assignment_template__questions__rubric",
            "assignment_template__questions__mcq_correct_answers",
            "question_groups",
            "questions",
            "teacher_criteria",
            "submissions__student",
            "submissions__teacher",
            "submissions__answers__question",
            "submissions__answers__multiple_choice__selected",
            "submissions__answers__short_answer",
            "submissions__answers__number_scale",
            "submissions__images",
        )
        .get(id=assignment_id)
    )


def _build_manifest(assignment: Assignment, request_user, identifiable: bool, participant_labels: dict[int, str]) -> dict:
    """Create a top-level manifest describing the archive bundle contents."""
    return {
        "version": 1,
        "generatedAt": timezone.now().isoformat(),
        "generatedByUserId": request_user.id,
        "identifiable": identifiable,
        "assignment": {
            "id": assignment.id,
            "title": assignment.title or assignment.assignment_template.title,
            "status": assignment.status,
            "courseId": assignment.course_id,
            "courseName": assignment.course.name if assignment.course else None,
        },
        "assignmentTemplate": {
            "id": assignment.assignment_template_id,
            "title": assignment.assignment_template.title,
            "category": assignment.assignment_template.category,
            "status": assignment.assignment_template.status,
        },
        "submissionCount": assignment.submissions.count(),
        "participants": [
            {"userId": user_id, "label": label}
            for user_id, label in sorted(participant_labels.items())
        ],
    }


def _build_participant_labels(assignment: Assignment) -> dict[int, str]:
    """Create stable anonymized labels for participants inside a single bundle."""
    labels: dict[int, str] = {}
    counter = 1
    for submission in assignment.submissions.all():
        owner_id = submission.student_id or submission.teacher_id
        if owner_id is None or owner_id in labels:
            continue
        labels[owner_id] = f"participant-{counter:03d}"
        counter += 1
    return labels


def _serialize_course(assignment: Assignment) -> dict:
    """Serialize minimal course metadata for archive context."""
    course = assignment.course
    if course is None:
        return {}
    return {
        "id": course.id,
        "name": course.name,
        "status": getattr(course, "status", None),
        "teacherName": getattr(getattr(course, "teacher_profile", None), "user", None).name
        if getattr(course, "teacher_profile", None)
        else None,
    }


def _render_submission_csv(
    submissions: list,
    identifiable: bool,
    participant_labels: dict[int, str],
) -> str:
    """Render a human-readable submissions CSV for the archive bundle."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    columns = [
        "submissionId",
        "participant",
        "status",
        "score",
        "submittedAt",
    ]
    if identifiable:
        columns.extend(["studentId", "studentName", "studentUsername"])
    writer.writerow(columns)
    for submission in submissions:
        participant = participant_labels.get(submission.student_id or submission.teacher_id, "-")
        row = [
            submission.id,
            participant,
            submission.status,
            submission.score if submission.score is not None else "",
            submission.submitted_at.isoformat() if submission.submitted_at else "",
        ]
        if identifiable:
            row.extend(
                [
                    submission.student_id or "",
                    submission.student.name if submission.student_id and submission.student else "",
                    submission.student.username if submission.student_id and submission.student else "",
                ]
            )
        writer.writerow(row)
    return buffer.getvalue()


def _serialize_rubrics(assignment: Assignment) -> dict[str, dict]:
    """Serialize rubric snapshots referenced by the template."""
    payloads: dict[str, dict] = {}
    snapshot = assignment.template_snapshot if isinstance(assignment.template_snapshot, dict) else {}
    rubric_snapshot = snapshot.get("rubrics") if isinstance(snapshot.get("rubrics"), dict) else {}
    if rubric_snapshot.get("template"):
        payloads["{root}/template/rubrics/template-rubric.json"] = rubric_snapshot["template"]
    for key, payload in rubric_snapshot.items():
        if key == "template" or not isinstance(payload, dict):
            continue
        payloads[f"{{root}}/template/rubrics/{key}.json"] = payload
    return payloads


def _get_template_snapshot_payload(assignment: Assignment) -> dict:
    """Return the frozen template payload used for bundle serialization."""
    snapshot = assignment.template_snapshot if isinstance(assignment.template_snapshot, dict) else {}
    payload = snapshot.get("template")
    return payload if isinstance(payload, dict) else {}


def _write_question_images(archive: ZipFile, assignment: Assignment, root: str) -> None:
    """Add question image binaries to the bundle when present."""
    backend = get_storage_backend()
    for question in assignment.questions.all():
        meta = _parse_snapshot_image(question.image)
        if not meta:
            continue
        storage_key = meta.get("storageKey")
        if not storage_key:
            continue
        try:
            data = backend.retrieve(storage_key)
        except FileNotFoundError:
            logger.warning("Question image missing during bundle generation: %s", storage_key)
            continue
        ext = Path(meta.get("originalFilename") or storage_key).suffix or ".bin"
        archive.writestr(
            f"{root}/template/question-images/question-{question.id}{ext}",
            data,
        )


def _parse_snapshot_image(raw_value: str | None) -> dict | None:
    """Parse assignment snapshot image metadata."""
    if not raw_value:
        return None
    try:
        payload = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_submission_payloads(
    archive: ZipFile,
    submissions: list,
    root: str,
    *,
    identifiable: bool,
    participant_labels: dict[int, str],
) -> None:
    """Write per-submission JSON payloads and image binaries into the bundle."""
    backend = get_storage_backend()
    for submission in submissions:
        sub_root = f"{root}/assignment/submissions/submission-{submission.id}"
        archive.writestr(
            f"{sub_root}/submission.json",
            json.dumps(
                _serialize_submission(submission, identifiable, participant_labels),
                indent=2,
                sort_keys=True,
            ),
        )
        for image in submission.images.exclude(status="DELETED"):
            try:
                data = backend.retrieve(image.storage_key)
            except FileNotFoundError:
                logger.warning(
                    "Submission image missing during bundle generation: %s",
                    image.storage_key,
                )
                continue
            ext = Path(image.original_filename or image.storage_key).suffix or ".bin"
            archive.writestr(
                f"{sub_root}/images/{image.id}{ext}",
                data,
            )


def _serialize_submission(submission, identifiable: bool, participant_labels: dict[int, str]) -> dict:
    """Serialize a submission and its answers for the archive bundle."""
    participant = participant_labels.get(submission.student_id or submission.teacher_id, "-")
    payload = {
        "id": submission.id,
        "participant": participant,
        "status": submission.status,
        "score": submission.score,
        "submittedAt": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "answers": [_serialize_answer(answer) for answer in submission.answers.all()],
        "images": [
            {
                "id": str(image.id),
                "originalFilename": image.original_filename,
                "mimeType": image.mime_type,
                "sizeBytes": image.size_bytes,
                "status": image.status,
            }
            for image in submission.images.exclude(status="DELETED")
        ],
    }
    if identifiable:
        payload["student"] = {
            "id": submission.student_id,
            "name": submission.student.name if submission.student_id and submission.student else None,
            "username": submission.student.username
            if submission.student_id and submission.student
            else None,
        }
    return payload


def _serialize_answer(answer) -> dict:
    """Serialize answer data into a JSON-safe dict."""
    payload = {
        "questionId": answer.question_id,
        "prompt": answer.question.prompt,
        "type": answer.answer_type,
        "score": answer.score,
        "skipped": answer.skipped,
    }
    if answer.answer_type == AnswerType.MULTIPLE_CHOICE:
        payload["value"] = {
            "selected": [item.choice_index for item in answer.multiple_choice.selected.all()]
        }
    elif answer.answer_type == AnswerType.SHORT_ANSWER:
        payload["value"] = {"text": answer.short_answer.text}
    elif answer.answer_type == AnswerType.NUMBER_SCALE:
        payload["value"] = {"val": answer.number_scale.val}
    else:
        payload["value"] = {}
    return payload


def _delete_artifact_file(file_path: str) -> None:
    """Delete an artifact file if it still exists."""
    path = Path(file_path)
    if path.exists():
        path.unlink()
