# FR-15 Image Upload (IMG) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | IMG |
| **Applies To** | ADMIN, RESEARCHER, TEACHER, STUDENT |
| **Related Issues** | TBD |
| **Dependencies** | FR-07 ASGN, FR-08 SUB, FR-11 OBS, FR-13 INFRA, FR-14 ARCH |

---

## 1) Scope

### In Scope
- Image upload for submission answers (SUB domain attachment).
- Student self-upload to own submission.
- Teacher proxy upload on behalf of students in teacher-owned courses/assignments.
- Image retrieval via protected API endpoint with Nginx internal redirect (X-Accel-Redirect).
- Standalone `SubmissionImage` model with FK to Submission.
- Filesystem storage abstraction: local disk in development, S3-compatible object store in production.
- Upload validation: MIME allowlist with magic byte verification, max file size, max images per submission, SHA-256 duplicate detection.
- EXIF metadata stripping on upload for privacy.
- Scan hook interface (auto-promotes to READY in non-production; production requires real scanner or explicit override flag).
- Soft-delete for user-initiated image removal (before submission only).
- Cascade hard-delete of images on parent submission purge (FR-14 ARCH).
- Audit events for all image mutations (FR-11 OBS).

### Out of Scope
- Profile avatar uploads.
- Assessment/assignment media attachments (question illustrations, diagrams).
- Thumbnail generation or image resizing.
- CDN edge caching (infrastructure upgrade, not API contract change).
- Video or non-image file uploads.
- Bulk upload endpoint.
- UI wireframes and Playwright flows.

### Core intent
- Allow students and teachers to attach image evidence to submission answers.
- Keep image storage, retrieval, and lifecycle well-separated from submission data.
- Enforce privacy (EXIF stripping), security (auth-gated serving, scan hook), and integrity (immutability after submit).

---

## 2) Actors

| Role | Type | IMG domain permissions |
|------|------|----------------------|
| ADMIN | System role (`is_staff=True`) | Read any image via SUB visibility rules; no direct upload role (inherits via override if needed) |
| RESEARCHER | User role | Read images on submissions visible per SUB/ASMT read gates; no upload or delete rights |
| TEACHER | User role | Proxy upload to submissions in teacher-owned courses/assignments; delete own-course images before submit; read images per SUB visibility |
| STUDENT | User role | Upload to own submission; delete own images before submit; read own submission images |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER > STUDENT

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| IMG-US-01 | STUDENT | As a student I can upload images to my submission to include visual evidence for my answers. |
| IMG-US-02 | TEACHER | As a teacher I can upload images on behalf of a student in my course when assisting with submissions. |
| IMG-US-03 | ADMIN, RESEARCHER, TEACHER | As a privileged user I can view images attached to submissions I have visibility to. |
| IMG-US-04 | STUDENT, TEACHER | As a student or teacher I can delete an uploaded image before the submission is submitted. |
| IMG-US-05 | ADMIN | As an admin I can rely on audit trails for all image upload and delete actions. |

---

## 4) Use Cases

### IMG-UC-01 — Student Upload Image

**Roles:** STUDENT (submission owner)
**Endpoint:** `POST /api/v1/submissions/{submission_id}/images`

**Main Flow:**
1. Student sends multipart upload with image file.
2. System validates submission exists and belongs to caller.
3. System validates submission status is `NOT_STARTED` or `IN_PROGRESS` (post-submit lock gate).
4. System validates file: MIME allowlist check, magic byte verification, size ≤ 10 MB.
5. System checks image count for submission < 10.
6. System computes SHA-256 hash and checks for duplicate (unique constraint on submission_id + sha256_hash).
7. System strips EXIF metadata from file.
8. System writes file to storage at `submissions/{submission_id}/{uuid}.{ext}`.
9. System creates `SubmissionImage` record with `status=PENDING_SCAN`.
10. Scan hook runs: in non-production, auto-promotes to `READY`; in production, requires real scanner or explicit override flag.
11. System emits `IMAGE_UPLOAD` audit event.
12. System returns image metadata DTO (id, original_filename, mime_type, size_bytes, status, created_at).

**Postconditions:**
- Image file stored on disk/S3.
- SubmissionImage record created with correct ownership fields.
- Audit event persisted.

**Errors:**
- `IMG-UC-01-E1`: Submission not found (`404`).
- `IMG-UC-01-E2`: Student does not own submission (`403`).
- `IMG-UC-01-E3`: Submission already submitted or graded — post-submit lock (`409`).
- `IMG-UC-01-E4`: Invalid MIME type or magic byte mismatch (`415`).
- `IMG-UC-01-E5`: File exceeds 10 MB (`413`).
- `IMG-UC-01-E6`: Image count limit reached — 10 per submission (`409`).
- `IMG-UC-01-E7`: Duplicate file hash for this submission (`409`).

**Tests (representative):**
- `test_IMG_UC_01_STUDENT`
- `test_IMG_UC_01_E2`
- `test_IMG_UC_01_E3_post_submit_lock`
- `test_IMG_UC_01_E4_invalid_mime`
- `test_IMG_UC_01_E5_file_too_large`
- `test_IMG_UC_01_E6_count_limit`
- `test_IMG_UC_01_E7_duplicate_hash`

---

### IMG-UC-02 — Teacher Proxy Upload

**Roles:** TEACHER (must own course/assignment the submission belongs to)
**Endpoint:** `POST /api/v1/submissions/{submission_id}/images`

**Main Flow:**
1. Teacher sends multipart upload with image file.
2. System validates submission exists.
3. System validates proxy upload gate: submission belongs to a course/assignment owned by calling teacher. Reject with `403` otherwise.
4. System validates submission status is `NOT_STARTED` or `IN_PROGRESS` (post-submit lock gate).
5. Steps 4–9 from IMG-UC-01 (validation, EXIF strip, storage, record creation).
6. System sets `uploaded_by_user_id` to teacher; `submission_owner_user_id` to student.
7. System emits `IMAGE_PROXY_UPLOAD` audit event (includes teacher actor and target student).
8. System returns image metadata DTO.

**Postconditions:**
- Image attributed to teacher as uploader, student as submission owner.
- Proxy upload audit event persisted with dual attribution.

**Errors:**
- `IMG-UC-02-E1`: Submission not found (`404`).
- `IMG-UC-02-E2`: Teacher does not own course/assignment for this submission (`403`).
- `IMG-UC-02-E3`: Submission already submitted or graded (`409`).
- `IMG-UC-02-E4..E7`: Same validation errors as IMG-UC-01-E4..E7.

**Tests (representative):**
- `test_IMG_UC_02_TEACHER_proxy`
- `test_IMG_UC_02_E2_not_owned_course`
- `test_IMG_UC_02_E3_post_submit_lock`
- `test_IMG_CN_04_proxy_upload_ownership_gate`
- `test_IMG_CN_05_dual_attribution`

---

### IMG-UC-03 — Retrieve Image

**Roles:** ADMIN, RESEARCHER, TEACHER, STUDENT (per SUB visibility rules)
**Endpoint:** `GET /api/v1/submissions/{submission_id}/images/{image_id}`

**Main Flow:**
1. Caller requests image.
2. System validates submission exists and caller has SUB read visibility.
3. System validates image exists, belongs to submission, and `status=READY`.
4. System sets response headers: `ETag` (sha256), `Last-Modified` (created_at), `Cache-Control: private`, `Content-Type`, `Content-Disposition: inline`.
5. Backend returns `X-Accel-Redirect` header pointing to internal Nginx location for the storage path.
6. Nginx streams the file to the client.

**Errors:**
- `IMG-UC-03-E1`: Submission not found (`404`).
- `IMG-UC-03-E2`: Caller lacks SUB read visibility (`403`).
- `IMG-UC-03-E3`: Image not found or not READY (`404`).

**Tests (representative):**
- `test_IMG_UC_03_STUDENT_own_submission`
- `test_IMG_UC_03_TEACHER_visible_submission`
- `test_IMG_UC_03_ADMIN`
- `test_IMG_UC_03_E2_no_visibility`
- `test_IMG_UC_03_E3_pending_scan_not_served`

---

### IMG-UC-04 — Delete Image (Soft Delete)

**Roles:** STUDENT (own submission), TEACHER (owned course/assignment proxy gate)
**Endpoint:** `DELETE /api/v1/submissions/{submission_id}/images/{image_id}`

**Main Flow:**
1. Caller requests image deletion.
2. System validates submission exists and caller has delete rights (student owns submission, or teacher owns course/assignment).
3. System validates submission status is `NOT_STARTED` or `IN_PROGRESS` (post-submit lock gate).
4. System validates image exists, belongs to submission, and `status != DELETED`.
5. System sets image `status=DELETED`, `deleted_at=now()`.
6. System emits `IMAGE_DELETE` audit event.
7. System returns `204 No Content`.
8. Async blob cleanup job removes file from storage (best-effort, idempotent).

**Postconditions:**
- Image metadata soft-deleted (hidden from list/retrieve).
- Blob scheduled for async cleanup.
- Audit event persisted.

**Errors:**
- `IMG-UC-04-E1`: Submission not found (`404`).
- `IMG-UC-04-E2`: Caller lacks delete rights (`403`).
- `IMG-UC-04-E3`: Submission already submitted or graded — post-submit lock (`409`).
- `IMG-UC-04-E4`: Image not found or already deleted (`404`).

**Tests (representative):**
- `test_IMG_UC_04_STUDENT_delete_own`
- `test_IMG_UC_04_TEACHER_proxy_delete`
- `test_IMG_UC_04_E2_not_owner`
- `test_IMG_UC_04_E3_post_submit_lock`
- `test_IMG_CN_08_delete_blocked_after_submit`

---

### IMG-UC-05 — List Images for Submission

**Roles:** ADMIN, RESEARCHER, TEACHER, STUDENT (per SUB visibility rules)
**Endpoint:** `GET /api/v1/submissions/{submission_id}/images`

**Main Flow:**
1. Caller requests image list.
2. System validates submission exists and caller has SUB read visibility.
3. System returns all images for submission where `status=READY`, ordered by `created_at`.
4. Response includes metadata only (id, original_filename, mime_type, size_bytes, uploaded_by_user_id, created_at). No binary data.

**Errors:**
- `IMG-UC-05-E1`: Submission not found (`404`).
- `IMG-UC-05-E2`: Caller lacks SUB read visibility (`403`).

**Tests (representative):**
- `test_IMG_UC_05_STUDENT_own_submission`
- `test_IMG_UC_05_TEACHER_visible`
- `test_IMG_UC_05_excludes_deleted_and_pending`

---

### IMG-UC-06 — Audit Image Mutations

**Roles:** System behavior (all upload/delete flows)
**Trigger:** Any successful or denied image mutation attempt

**Main Flow:**
1. Service emits audit event with actor, action, target submission/image, filename, sha256, and outcome.
2. Audit record is persisted according to OBS policy.
3. Failure to persist audit log is handled per FR-11 rules.

**Audit Actions:**
- `IMAGE_UPLOAD` — student self-upload
- `IMAGE_PROXY_UPLOAD` — teacher on-behalf upload (includes target student)
- `IMAGE_DELETE` — soft-delete

**Audit Payload Minimum:**
- actor user id
- action
- submission_id
- image_id
- original_filename
- sha256_hash
- outcome (`SUCCESS`, `FAILURE`, `DENIED`)
- timestamp

**Tests (representative):**
- `test_IMG_UC_06_upload_emits_audit`
- `test_IMG_UC_06_proxy_upload_emits_audit`
- `test_IMG_UC_06_delete_emits_audit`

---

## 5) Constraints

### IMG-CN-01 — MIME Allowlist with Magic Byte Verification
- Accepted types: `image/jpeg`, `image/png`, `image/webp`.
- System must verify both `Content-Type` header and file magic bytes match an allowed type.
- Mismatches rejected with `415`.
- Applies to: IMG-UC-01, IMG-UC-02.

### IMG-CN-02 — Max File Size
- Per-image upload limit: 10 MB.
- Enforced at Nginx level (`client_max_body_size`) and backend level.
- Oversized uploads rejected with `413`.
- Applies to: IMG-UC-01, IMG-UC-02.

### IMG-CN-03 — Max Images Per Submission
- Maximum 10 images per submission.
- Count includes `READY` and `PENDING_SCAN` images; excludes `DELETED` and `REJECTED`.
- Exceeded limit rejected with `409`.
- Applies to: IMG-UC-01, IMG-UC-02.

### IMG-CN-04 — Proxy Upload Ownership Gate
- Teacher proxy upload is allowed only when the submission belongs to a course/assignment owned by the calling teacher.
- Non-owned submissions rejected with `403`.
- Applies to: IMG-UC-02.

### IMG-CN-05 — Dual Attribution
- Every `SubmissionImage` records both `uploaded_by_user_id` (actor who uploaded) and `submission_owner_user_id` (student who owns the submission).
- For student self-upload, both fields reference the same user.
- For teacher proxy upload, `uploaded_by_user_id` is the teacher and `submission_owner_user_id` is the student.
- Applies to: IMG-UC-01, IMG-UC-02.

### IMG-CN-06 — Duplicate Detection
- Unique constraint on `(submission_id, sha256_hash)`.
- Duplicate uploads to the same submission rejected with `409`.
- Applies to: IMG-UC-01, IMG-UC-02.

### IMG-CN-07 — EXIF Metadata Stripping
- All uploaded images must have EXIF metadata stripped before storage.
- Stripping removes GPS coordinates, device identifiers, timestamps, and other embedded metadata.
- Applies to: IMG-UC-01, IMG-UC-02.

### IMG-CN-08 — Post-Submit Lock
- Upload and delete operations are blocked when submission status is `SUBMITTED` or `GRADED`.
- Only `NOT_STARTED` and `IN_PROGRESS` submissions accept image mutations.
- Blocked operations rejected with `409`.
- Applies to: IMG-UC-01, IMG-UC-02, IMG-UC-04.

### IMG-CN-09 — Scan Hook Interface
- Upload pipeline includes a scan hook invoked after file storage and before status promotion.
- In non-production environments, the scan hook auto-promotes images from `PENDING_SCAN` to `READY`.
- In production, a real scanner must be configured or the environment variable `IMG_ALLOW_UNSCANNED_UPLOADS` must be explicitly set to `true` (default: `false`). When `false` and no scanner is configured, uploads remain `PENDING_SCAN` indefinitely and are not served.
- On scan failure, image status is set to `REJECTED` and file is quarantined (retained but not served).
- Applies to: IMG-UC-01, IMG-UC-02.

### IMG-CN-10 — Storage Key Pattern
- Image files stored at path: `submissions/{submission_id}/{uuid}.{ext}`.
- UUID is generated per image; extension matches validated MIME type.
- Original filename preserved in DB metadata only, never used in storage path.
- Applies to: IMG-UC-01, IMG-UC-02.

### IMG-CN-11 — Protected Serving via Nginx Internal Redirect
- Images served through protected API endpoint; backend validates auth and permissions.
- Backend returns `X-Accel-Redirect` header to Nginx for file streaming.
- Response includes `ETag` (sha256), `Last-Modified`, `Cache-Control: private`, `Content-Type`, `Content-Disposition: inline`.
- No public URLs or direct storage access exposed to clients.
- Applies to: IMG-UC-03.

### IMG-CN-12 — Cascade Delete on Parent Purge
- When a submission is purged (FR-14 ARCH-UC-06), all associated `SubmissionImage` records and their storage blobs are hard-deleted.
- Purge workflow deletes DB metadata and storage blobs in one operation with retry/idempotency handling if blob delete fails.
- Applies to: FR-14 ARCH-UC-06.

### IMG-CN-13 — Audit Required for Image Mutations
- All image uploads (self and proxy) and deletes must emit audit events.
- Proxy uploads must include both actor (teacher) and target student in audit payload.
- Audit payload must include actor, submission_id, image_id, filename, sha256, action, outcome, timestamp.
- Applies to: IMG-UC-06.

### IMG-CN-14 — Error Semantics
- `400` for malformed request (missing file, bad multipart).
- `403` for permission/ownership violations.
- `404` for unknown submission or image.
- `409` for lifecycle conflicts (post-submit lock, count limit, duplicate hash).
- `413` for oversized file.
- `415` for invalid MIME type or magic byte mismatch.
- Applies to: IMG-UC-01..05.

### IMG-CN-15 — Storage Abstraction
- Image storage backend must be configurable via abstraction layer.
- Local filesystem for development; S3-compatible object store for production.
- Storage interface exposes: `store(key, data)`, `retrieve(key)`, `delete(key)`, `exists(key)`.
- No storage-provider-specific logic in upload/serve/delete use case code.
- Applies to: IMG-UC-01..04.

---

## 6) Infrastructure Contract

### 6.1 Data Contract

`SubmissionImage` model:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID PK | Image identifier |
| `submission_id` | FK (indexed) | Parent submission |
| `uploaded_by_user_id` | FK | User who performed the upload (student or teacher) |
| `submission_owner_user_id` | FK | Student who owns the submission (denormalized for audit/query) |
| `storage_key` | varchar (unique) | Path/key in storage backend |
| `original_filename` | varchar | Original client filename (metadata only) |
| `mime_type` | varchar | Validated MIME type |
| `size_bytes` | integer | File size in bytes |
| `sha256_hash` | varchar | SHA-256 hash of file content |
| `status` | enum | `PENDING_SCAN`, `READY`, `REJECTED`, `DELETED` |
| `created_at` | datetime | Upload timestamp |
| `deleted_at` | datetime nullable | Soft-delete timestamp |

**Constraints/Indexes:**
- `unique(submission_id, sha256_hash)` — duplicate detection
- `index(submission_id, status)` — filtered list queries
- `check(size_bytes > 0)` — data integrity

### 6.2 Validation Constants

| Constant | Value | Enforced At |
|----------|-------|-------------|
| `IMG_ALLOWED_MIME_TYPES` | `image/jpeg`, `image/png`, `image/webp` | Backend (MIME + magic byte) |
| `IMG_MAX_FILE_SIZE_BYTES` | `10485760` (10 MB) | Nginx (`client_max_body_size`), Backend |
| `IMG_MAX_IMAGES_PER_SUBMISSION` | `10` | Backend |
| `IMG_ALLOW_UNSCANNED_UPLOADS` | `false` | Backend (production default) |

### 6.3 Endpoint Contract

| Method | Endpoint | Auth + visibility gate | Use Case |
|--------|----------|------------------------|----------|
| POST | `/api/v1/submissions/{submission_id}/images` | Submission owner (student) or course/assignment owner (teacher proxy) | IMG-UC-01, IMG-UC-02 |
| GET | `/api/v1/submissions/{submission_id}/images` | SUB read visibility | IMG-UC-05 |
| GET | `/api/v1/submissions/{submission_id}/images/{image_id}` | SUB read visibility | IMG-UC-03 |
| DELETE | `/api/v1/submissions/{submission_id}/images/{image_id}` | Submission owner or teacher proxy + pre-submit gate | IMG-UC-04 |

### 6.4 Nginx Contract

| Directive | Value | Purpose |
|-----------|-------|---------|
| `client_max_body_size` | `10m` | Enforce upload size at reverse proxy |
| `internal` location | `/internal/media/submissions/` | X-Accel-Redirect target for image serving |

### 6.5 Storage Contract

| Environment | Backend | Base Path |
|-------------|---------|-----------|
| Development | Local filesystem | `{MEDIA_ROOT}/submissions/` |
| Production | S3-compatible | `{S3_BUCKET}/submissions/` |

Key format: `submissions/{submission_id}/{uuid}.{ext}`

### 6.6 Audit Contract

Audit actions (FR-11) for IMG:
- `IMAGE_UPLOAD`
- `IMAGE_PROXY_UPLOAD`
- `IMAGE_DELETE`

Audit payload minimum:
- actor user id
- action
- submission_id
- image_id
- original_filename
- sha256_hash
- outcome (`SUCCESS`, `FAILURE`, `DENIED`)
- timestamp

---

## 7) Error Model

| Scenario | Behavior | Contract |
|----------|----------|----------|
| Upload to missing submission | Return not found | `404` |
| Student uploads to non-owned submission | Reject | `403` |
| Teacher uploads to non-owned course submission | Reject | `403` |
| Upload to submitted/graded submission | Reject post-submit lock | `409` |
| Invalid MIME type or magic byte mismatch | Reject | `415` |
| File exceeds 10 MB | Reject | `413` |
| Image count limit reached (10) | Reject | `409` |
| Duplicate file hash for submission | Reject | `409` |
| Retrieve image with PENDING_SCAN status | Return not found | `404` |
| Retrieve from non-visible submission | Reject | `403` |
| Delete after submission submitted/graded | Reject post-submit lock | `409` |
| Delete already-deleted image | Return not found | `404` |
| Malformed multipart request | Reject | `400` |

---

## 8) Test Strategy by Layer

### Naming Convention
- UC tests: `test_IMG_UC_##[_ROLE|_E#]`
- Constraint tests: `test_IMG_CN_##_*`
- System tests: `ST-IMG-UC-##` / `ST-IMG-CN-##`

### Backend Unit
- MIME + magic byte validator (allow/reject cases).
- SHA-256 hash computation and duplicate check.
- EXIF stripping verification.
- Storage key generation.
- Post-submit lock gate logic.
- Proxy upload ownership evaluator.

### Backend Integration
- Full upload flow (student self, teacher proxy) with file storage and DB record creation.
- Retrieve flow with X-Accel-Redirect header verification.
- Delete flow with soft-delete and blob cleanup.
- Post-submit lock enforcement across upload and delete.
- Duplicate detection across upload attempts.
- Audit event emission for all mutation paths.
- Scan hook behavior in non-production (auto-promote) and production (require scanner).

### System Tests (Black Box)
- `ST-IMG-UC-01` student uploads image, retrieves it, verifies content.
- `ST-IMG-UC-02` teacher proxy uploads image, verify dual attribution in audit.
- `ST-IMG-UC-03` retrieve image via protected endpoint, verify headers and content.
- `ST-IMG-UC-04` delete image before submit, verify hidden from list.
- `ST-IMG-CN-08` upload and delete blocked after submission submitted.
- `ST-IMG-CN-12` purge submission, verify images and blobs removed.
- `ST-IMG-CN-13` audit entries exist for upload, proxy upload, and delete.

---

## 9) NFR Cross-References

- **Security**
  - Auth-gated serving via protected endpoint, no public URLs (IMG-CN-11).
  - MIME + magic byte validation prevents content-type spoofing (IMG-CN-01).
  - Proxy upload ownership gate prevents unauthorized teacher access (IMG-CN-04).
  - Scan hook interface for malware detection (IMG-CN-09).
- **Privacy**
  - EXIF metadata stripping removes location and device data (IMG-CN-07).
  - Cache-Control: private prevents shared cache leakage (IMG-CN-11).
- **Data Integrity**
  - SHA-256 duplicate detection (IMG-CN-06).
  - Post-submit lock prevents mutation of submitted work (IMG-CN-08).
  - Dual attribution preserves upload provenance (IMG-CN-05).
- **Reliability**
  - Storage abstraction enables backend portability (IMG-CN-15).
  - Purge with retry/idempotency for blob cleanup (IMG-CN-12).
- **Auditability**
  - Mandatory mutation audit events (IMG-CN-13).

---

## 10) Cross-Domain References

| Domain | IMG dependency | Integration note |
|--------|----------------|------------------|
| FR-07 ASGN | Assignment ownership for teacher proxy gate | Teacher proxy upload requires assignment owned by calling teacher. |
| FR-08 SUB | Submission ownership, status gates, read visibility | IMG inherits SUB visibility rules for read access. Post-submit lock uses SUB status. |
| FR-11 OBS | Audit event emission | IMAGE_UPLOAD, IMAGE_PROXY_UPLOAD, IMAGE_DELETE actions emitted per OBS policy. |
| FR-13 INFRA | Nginx config, storage backend, Docker volumes | X-Accel-Redirect Nginx location, S3/filesystem backend config, MEDIA_ROOT volume mount. |
| FR-14 ARCH | Cascade delete on purge, archive status gates | Images follow submission lifecycle. Parent purge hard-deletes image metadata and blobs. Archived assignment blocks new uploads via SUB status gate. |

---

## 11) Current Implementation Alignment Notes

Current implementation is aligned with the FR-15 target contract for image upload, retrieval, deletion, and auditability.

Implemented alignment:
1. **SubmissionImage model and lifecycle states exist.** `PENDING_SCAN`, `READY`, `REJECTED`, and `DELETED` are implemented with metadata, indexing, and integrity constraints.
2. **Upload/retrieve/delete/list endpoints are implemented.** Student self-upload, teacher proxy upload, visibility-gated retrieval, and soft-delete are available under SUB routes.
3. **Validation pipeline is implemented.** MIME allowlist + magic-byte checks, file size limits, per-submission count limits, duplicate detection, and post-submit lock are enforced.
4. **EXIF stripping is implemented.** Uploads are normalized via Pillow prior to storage and hashing.
5. **Storage abstraction is implemented.** Local storage backend abstraction exists with idempotent delete behavior; serving uses protected `X-Accel-Redirect`.
6. **Scan hook behavior is implemented.** Non-production (or explicit override) auto-promotes to `READY`; production-safe pending behavior is supported.
7. **Audit events are implemented.** `IMAGE_UPLOAD`, `IMAGE_PROXY_UPLOAD`, and `IMAGE_DELETE` actions are emitted with two-phase audit completion.
8. **Purge cascade is wired.** FR-14 assignment purge flow cleans up submission image metadata and blobs.
9. **Infrastructure wiring is in place.** `MEDIA_ROOT` settings, env toggles, Docker media mount, and Nginx internal media location are configured.
10. **IMG integration coverage exists.** FR-traceable IMG UC/CN integration tests are present and passing in the backend suite.
