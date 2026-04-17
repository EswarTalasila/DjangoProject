"""FR-15 Image Upload — integration tests with traceability.

Naming convention:
  test_IMG_UC_XX_<scenario>   — use-case happy / alt paths
  test_IMG_CN_XX_<scenario>   — constraint verification
"""

import io
import struct
import tempfile

import pytest
from django.conf import settings
from django.utils import timezone

from assignment_templates.models import AssignmentTemplate, GradingMode, Question, QuestionKind, ScoringPolicy
from assignments.models import Assignment, AssignmentStatus
from core.models import AuditAction, AuditLog
from courses.models import Course, Enrollment, EnrollmentStatus
from submissions.models import ImageStatus, Submission, SubmissionImage, SubmissionStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_course_assignment(teacher_user, student_user, admin_user):
    """Create a minimal course → assignment_template → assignment → enrollment → submission graph."""
    assignment_template = AssignmentTemplate.objects.create(
        title="IMG Test AssignmentTemplate",
        grading_mode=GradingMode.MANUAL,
        scoring_policy=ScoringPolicy.STANDARD,
        created_by_admin=admin_user,
    )
    Question.objects.create(
        assignment_template=assignment_template,
        question_type=QuestionKind.SHORT_ANSWER,
        kind=QuestionKind.SHORT_ANSWER,
        prompt="Q1",
        max_points=5.0,
        auto_gradable=False,
        graded=False,
    )
    course = Course.objects.create(
        name="IMG Course",
        teacher_profile=teacher_user.teacher_profile,
    )
    Enrollment.objects.create(
        course=course,
        student_profile=student_user.student_profile,
        status=EnrollmentStatus.ACTIVE,
    )
    assignment = Assignment.objects.create(
        assignment_template=assignment_template,
        audience_type="COURSE",
        course=course,
        created_by=teacher_user,
        open_at=timezone.now(),
    )
    submission = Submission.objects.create(
        assignment=assignment,
        student=student_user,
        status=SubmissionStatus.IN_PROGRESS,
    )
    return assignment, submission, course


def _make_jpeg_bytes(size=100):
    """Create minimal valid JPEG bytes (FFD8FF header)."""
    # Minimal JPEG: SOI + APP0 + EOI
    header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    footer = b"\xff\xd9"
    # Pad to desired size
    padding = b"\x00" * max(0, size - len(header) - len(footer))
    return header + padding + footer


def _make_png_bytes(size=100):
    """Create minimal valid PNG bytes."""
    # PNG signature + minimal IHDR + IEND
    sig = b"\x89PNG\r\n\x1a\n"
    # IHDR: 13 bytes, 1x1, 8-bit RGB
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    import zlib

    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
    data = sig + ihdr + iend
    padding = b"\x00" * max(0, size - len(data))
    return data + padding


def _make_webp_bytes(size=100):
    """Create minimal valid WebP bytes (RIFF....WEBP header)."""
    body = b"\x00" * max(0, size - 12)
    file_size = len(body) + 4  # 4 for WEBP
    return b"RIFF" + struct.pack("<I", file_size) + b"WEBP" + body


def _upload_file(api_client, submission_id, content=None, filename="test.jpg", content_type="image/jpeg"):
    """Helper to POST an image upload."""
    if content is None:
        content = _make_jpeg_bytes()
    f = io.BytesIO(content)
    f.name = filename
    return api_client.post(
        f"/api/v1/submissions/{submission_id}/images",
        {"file": f},
        format="multipart",
        HTTP_CONTENT_TYPE=content_type,
    )


def _upload_simple_file(api_client, submission_id, content_type="image/jpeg"):
    """Upload a simple in-memory file via multipart."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    if content_type == "image/jpeg":
        data = _make_jpeg_bytes(200)
        ext = "jpg"
    elif content_type == "image/png":
        data = _make_png_bytes(200)
        ext = "png"
    else:
        data = _make_webp_bytes(200)
        ext = "webp"

    f = SimpleUploadedFile(f"test.{ext}", data, content_type=content_type)
    return api_client.post(
        f"/api/v1/submissions/{submission_id}/images",
        {"file": f},
        format="multipart",
    )


# ---------------------------------------------------------------------------
# IMG-UC-01 — Student Upload Image
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStudentUpload:
    """IMG-UC-01: POST /submissions/{id}/images (student self-upload)"""

    def test_IMG_UC_01_STUDENT(self, api_client, teacher_user, student_user, admin_user, tmp_path):
        """Student uploads image successfully — 201."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)

        r = _upload_simple_file(api_client, submission.id)
        assert r.status_code == 201, r.data
        assert r.data["mimeType"] == "image/jpeg"
        assert r.data["status"] == "READY"  # non-prod auto-promote
        assert r.data["uploadedByUserId"] == student_user.id

    def test_IMG_UC_01_E1_submission_not_found(self, api_client, student_user):
        """Upload to nonexistent submission — 404."""
        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, 999999)
        assert r.status_code == 404

    def test_IMG_UC_01_E2_not_owner(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Student uploads to another student's submission — 403."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        # Create a second student
        from tests.factories import UserFactory
        from accounts.models import Role, StudentProfile, UserRole

        other = UserFactory()
        UserRole.objects.create(user=other, role=Role.STUDENT)
        StudentProfile.objects.create(user=other, created_by=admin_user, consent=False)

        api_client.force_authenticate(user=other)
        r = _upload_simple_file(api_client, submission.id)
        assert r.status_code == 403

    def test_IMG_UC_01_E3_post_submit_lock(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Upload to submitted submission — 409."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        submission.status = SubmissionStatus.SUBMITTED
        submission.submitted_at = timezone.now()
        submission.save()

        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, submission.id)
        assert r.status_code == 409

    def test_IMG_UC_01_E4_invalid_mime(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Upload with invalid MIME type — 415."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)

        from django.core.files.uploadedfile import SimpleUploadedFile

        f = SimpleUploadedFile("test.txt", b"not an image", content_type="text/plain")
        r = api_client.post(
            f"/api/v1/submissions/{submission.id}/images",
            {"file": f},
            format="multipart",
        )
        assert r.status_code == 415

    def test_IMG_UC_01_E4_magic_mismatch(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Upload claiming JPEG but with PNG magic bytes — 415."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)

        from django.core.files.uploadedfile import SimpleUploadedFile

        # PNG bytes but claiming JPEG content type
        f = SimpleUploadedFile("fake.jpg", _make_png_bytes(), content_type="image/jpeg")
        r = api_client.post(
            f"/api/v1/submissions/{submission.id}/images",
            {"file": f},
            format="multipart",
        )
        assert r.status_code == 415

    def test_IMG_UC_01_E5_file_too_large(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Upload file exceeding 10 MB — 413."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)

        from django.core.files.uploadedfile import SimpleUploadedFile

        big_data = _make_jpeg_bytes(settings.IMG_MAX_FILE_SIZE_BYTES + 1024)
        f = SimpleUploadedFile("big.jpg", big_data, content_type="image/jpeg")
        r = api_client.post(
            f"/api/v1/submissions/{submission.id}/images",
            {"file": f},
            format="multipart",
        )
        assert r.status_code == 413

    def test_IMG_UC_01_E6_count_limit(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Upload when 10 images already exist — 409."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        # Pre-create 10 READY images
        import uuid

        for i in range(10):
            SubmissionImage.objects.create(
                submission=submission,
                uploaded_by=student_user,
                submission_owner=student_user,
                storage_key=f"submissions/{submission.id}/{uuid.uuid4()}.jpg",
                original_filename=f"img{i}.jpg",
                mime_type="image/jpeg",
                size_bytes=100,
                sha256_hash=f"{'%064x' % i}",
                status=ImageStatus.READY,
            )

        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, submission.id)
        assert r.status_code == 409

    def test_IMG_UC_01_E7_duplicate_hash(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Upload same file twice — second returns 409."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)

        # First upload succeeds
        r1 = _upload_simple_file(api_client, submission.id)
        assert r1.status_code == 201

        # Same file again → duplicate
        r2 = _upload_simple_file(api_client, submission.id)
        assert r2.status_code == 409

    def test_IMG_UC_01_malformed_multipart(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Upload with no file field — 400."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)

        r = api_client.post(
            f"/api/v1/submissions/{submission.id}/images",
            {},
            format="multipart",
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# IMG-UC-02 — Teacher Proxy Upload
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTeacherProxyUpload:
    """IMG-UC-02: POST /submissions/{id}/images (teacher proxy)"""

    def test_IMG_UC_02_TEACHER_proxy(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Teacher uploads to student's submission — 201."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=teacher_user)

        r = _upload_simple_file(api_client, submission.id)
        assert r.status_code == 201
        assert r.data["uploadedByUserId"] == teacher_user.id

    def test_IMG_UC_02_E2_not_owned_course(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Teacher uploads to submission in another teacher's course — 403."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)

        # Create another teacher
        from tests.factories import UserFactory
        from accounts.models import Role, TeacherProfile, UserRole

        other_teacher = UserFactory()
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher)

        api_client.force_authenticate(user=other_teacher)
        r = _upload_simple_file(api_client, submission.id)
        assert r.status_code == 403

    def test_IMG_UC_02_E3_post_submit_lock(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Teacher upload to submitted submission — 409."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        submission.status = SubmissionStatus.SUBMITTED
        submission.submitted_at = timezone.now()
        submission.save()

        api_client.force_authenticate(user=teacher_user)
        r = _upload_simple_file(api_client, submission.id)
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# IMG-UC-03 — Retrieve Image
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRetrieveImage:
    """IMG-UC-03: GET /submissions/{id}/images/{image_id}"""

    def _upload_and_get_id(self, api_client, submission, user, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        api_client.force_authenticate(user=user)
        r = _upload_simple_file(api_client, submission.id)
        assert r.status_code == 201
        return r.data["id"]

    def test_IMG_UC_03_STUDENT_own_submission(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Student retrieves own image — 200 with backend-streamed bytes."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        image_id = self._upload_and_get_id(api_client, submission, student_user, tmp_path)

        r = api_client.get(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 200
        assert r.content
        assert "X-Accel-Redirect" not in r
        assert r["Cache-Control"] == "private"

    def test_IMG_UC_03_TEACHER_visible_submission(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Teacher retrieves image from owned course — 200."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        image_id = self._upload_and_get_id(api_client, submission, student_user, tmp_path)

        api_client.force_authenticate(user=teacher_user)
        r = api_client.get(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 200

    def test_IMG_UC_03_ADMIN(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Admin retrieves any image — 200."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        image_id = self._upload_and_get_id(api_client, submission, student_user, tmp_path)

        api_client.force_authenticate(user=admin_user)
        r = api_client.get(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 200

    def test_IMG_UC_03_E2_no_visibility(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Other student cannot retrieve — 403."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        image_id = self._upload_and_get_id(api_client, submission, student_user, tmp_path)

        from tests.factories import UserFactory
        from accounts.models import Role, StudentProfile, UserRole

        other = UserFactory()
        UserRole.objects.create(user=other, role=Role.STUDENT)
        StudentProfile.objects.create(user=other, created_by=admin_user, consent=False)

        api_client.force_authenticate(user=other)
        r = api_client.get(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 403

    def test_IMG_UC_03_E3_pending_scan_not_served(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """PENDING_SCAN image returns 404."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, submission.id)
        image_id = r.data["id"]
        # Force to PENDING_SCAN
        SubmissionImage.objects.filter(id=image_id).update(status=ImageStatus.PENDING_SCAN)

        r = api_client.get(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 404

    def test_IMG_UC_03_E3_rejected_not_served(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """REJECTED image returns 404."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, submission.id)
        image_id = r.data["id"]
        SubmissionImage.objects.filter(id=image_id).update(status=ImageStatus.REJECTED)

        r = api_client.get(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 404

    def test_IMG_UC_03_E3_deleted_not_served(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """DELETED image returns 404."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, submission.id)
        image_id = r.data["id"]
        SubmissionImage.objects.filter(id=image_id).update(
            status=ImageStatus.DELETED, deleted_at=timezone.now()
        )

        r = api_client.get(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# IMG-UC-04 — Delete Image
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDeleteImage:
    """IMG-UC-04: DELETE /submissions/{id}/images/{image_id}"""

    def test_IMG_UC_04_STUDENT_delete_own(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Student deletes own image — 204."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, submission.id)
        image_id = r.data["id"]

        r = api_client.delete(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 204

        img = SubmissionImage.objects.get(id=image_id)
        assert img.status == ImageStatus.DELETED
        assert img.deleted_at is not None

    def test_IMG_UC_04_TEACHER_proxy_delete(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Teacher deletes image from owned course — 204."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, submission.id)
        image_id = r.data["id"]

        api_client.force_authenticate(user=teacher_user)
        r = api_client.delete(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 204

    def test_IMG_UC_04_E2_not_owner(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Other student cannot delete — 403."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, submission.id)
        image_id = r.data["id"]

        from tests.factories import UserFactory
        from accounts.models import Role, StudentProfile, UserRole

        other = UserFactory()
        UserRole.objects.create(user=other, role=Role.STUDENT)
        StudentProfile.objects.create(user=other, created_by=admin_user, consent=False)

        api_client.force_authenticate(user=other)
        r = api_client.delete(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 403

    def test_IMG_UC_04_E3_post_submit_lock(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Delete on submitted submission — 409."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, submission.id)
        image_id = r.data["id"]

        submission.status = SubmissionStatus.SUBMITTED
        submission.submitted_at = timezone.now()
        submission.save()

        r = api_client.delete(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 409

    def test_IMG_UC_04_E4_already_deleted(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Delete already-deleted image — 404."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, submission.id)
        image_id = r.data["id"]

        # Delete once
        r = api_client.delete(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 204
        # Delete again
        r = api_client.delete(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# IMG-UC-05 — List Images
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListImages:
    """IMG-UC-05: GET /submissions/{id}/images"""

    def test_IMG_UC_05_STUDENT_own_submission(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Student lists own submission images — 200."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        _upload_simple_file(api_client, submission.id)

        r = api_client.get(f"/api/v1/submissions/{submission.id}/images")
        assert r.status_code == 200
        assert len(r.data) == 1

    def test_IMG_UC_05_TEACHER_visible(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Teacher lists images from owned course — 200."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        _upload_simple_file(api_client, submission.id)

        api_client.force_authenticate(user=teacher_user)
        r = api_client.get(f"/api/v1/submissions/{submission.id}/images")
        assert r.status_code == 200
        assert len(r.data) == 1

    def test_IMG_UC_05_excludes_deleted_and_pending(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """List excludes DELETED and PENDING_SCAN images."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)

        # Upload 2 images
        r1 = _upload_simple_file(api_client, submission.id, content_type="image/jpeg")
        r2 = _upload_simple_file(api_client, submission.id, content_type="image/png")
        assert r1.status_code == 201
        assert r2.status_code == 201

        # Soft-delete first, set second to PENDING_SCAN
        SubmissionImage.objects.filter(id=r1.data["id"]).update(
            status=ImageStatus.DELETED, deleted_at=timezone.now()
        )
        SubmissionImage.objects.filter(id=r2.data["id"]).update(
            status=ImageStatus.PENDING_SCAN
        )

        r = api_client.get(f"/api/v1/submissions/{submission.id}/images")
        assert r.status_code == 200
        assert len(r.data) == 0


# ---------------------------------------------------------------------------
# IMG-UC-06 — Audit Events
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAuditEvents:
    """IMG-UC-06: Audit trail for image mutations"""

    def test_IMG_UC_06_upload_emits_audit(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Student upload creates IMAGE_UPLOAD audit entry."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        _upload_simple_file(api_client, submission.id)

        entry = AuditLog.objects.filter(action=AuditAction.IMAGE_UPLOAD).first()
        assert entry is not None
        assert entry.actor_id == student_user.id
        assert entry.outcome == "SUCCESS"

    def test_IMG_UC_06_proxy_upload_emits_audit(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Teacher proxy upload creates IMAGE_PROXY_UPLOAD audit entry."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=teacher_user)
        _upload_simple_file(api_client, submission.id)

        entry = AuditLog.objects.filter(action=AuditAction.IMAGE_PROXY_UPLOAD).first()
        assert entry is not None
        assert entry.actor_id == teacher_user.id

    def test_IMG_UC_06_delete_emits_audit(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Delete creates IMAGE_DELETE audit entry."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, submission.id)
        image_id = r.data["id"]

        api_client.delete(f"/api/v1/submissions/{submission.id}/images/{image_id}")

        entry = AuditLog.objects.filter(action=AuditAction.IMAGE_DELETE).first()
        assert entry is not None
        assert entry.actor_id == student_user.id


# ---------------------------------------------------------------------------
# IMG-CN — Constraint Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConstraints:
    """IMG constraint verification tests."""

    def test_IMG_CN_04_proxy_upload_ownership_gate(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Teacher cannot upload to non-owned course submission — 403."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)

        from tests.factories import UserFactory
        from accounts.models import Role, TeacherProfile, UserRole

        other_teacher = UserFactory()
        UserRole.objects.create(user=other_teacher, role=Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher)

        api_client.force_authenticate(user=other_teacher)
        r = _upload_simple_file(api_client, submission.id)
        assert r.status_code == 403

    def test_IMG_CN_05_dual_attribution(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Teacher proxy upload records both uploader and owner."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=teacher_user)
        r = _upload_simple_file(api_client, submission.id)
        assert r.status_code == 201

        img = SubmissionImage.objects.get(id=r.data["id"])
        assert img.uploaded_by_id == teacher_user.id
        assert img.submission_owner_id == student_user.id

    def test_IMG_CN_08_delete_blocked_after_submit(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Delete blocked on submitted submission — 409."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)
        r = _upload_simple_file(api_client, submission.id)
        image_id = r.data["id"]

        submission.status = SubmissionStatus.GRADED
        submission.submitted_at = timezone.now()
        submission.save()

        r = api_client.delete(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r.status_code == 409

    def test_IMG_CN_reupload_after_delete(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Re-upload same file after soft-delete succeeds."""
        settings.MEDIA_ROOT = str(tmp_path)
        _, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)
        api_client.force_authenticate(user=student_user)

        # Upload
        r1 = _upload_simple_file(api_client, submission.id)
        assert r1.status_code == 201
        image_id = r1.data["id"]

        # Delete
        r2 = api_client.delete(f"/api/v1/submissions/{submission.id}/images/{image_id}")
        assert r2.status_code == 204

        # Re-upload same content
        r3 = _upload_simple_file(api_client, submission.id)
        assert r3.status_code == 201

    def test_IMG_CN_12_purge_cascades_images(
        self, api_client, teacher_user, student_user, admin_user, tmp_path
    ):
        """Purge assignment removes images and blobs."""
        settings.MEDIA_ROOT = str(tmp_path)
        settings.IMAGE_ROOT = tmp_path / "images"
        settings.SUBMISSION_IMAGE_DIR = tmp_path / "images" / "submissions"
        assignment, submission, _ = _setup_course_assignment(teacher_user, student_user, admin_user)

        # Reset to NOT_STARTED so purge is allowed
        submission.status = SubmissionStatus.NOT_STARTED
        submission.save()

        api_client.force_authenticate(user=student_user)
        # Need IN_PROGRESS to upload
        submission.status = SubmissionStatus.IN_PROGRESS
        submission.save()
        r = _upload_simple_file(api_client, submission.id)
        assert r.status_code == 201
        image_id = r.data["id"]

        # Get storage key for blob verification
        img = SubmissionImage.objects.get(id=image_id)
        storage_key = img.storage_key
        blob_path = tmp_path / "images" / storage_key
        assert blob_path.exists()

        # Reset to NOT_STARTED and archive for purge
        submission.status = SubmissionStatus.NOT_STARTED
        submission.save()
        assignment.status = AssignmentStatus.ARCHIVED
        assignment.save()

        # Purge
        from assignments.services import purge_assignment

        purge_assignment(assignment)

        # Verify cleanup
        assert not SubmissionImage.objects.filter(id=image_id).exists()
        assert not blob_path.exists()
