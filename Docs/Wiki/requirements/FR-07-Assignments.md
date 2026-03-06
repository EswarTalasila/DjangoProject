# FR-07 Assignments (ASGN) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | ASGN |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER, STUDENT |
| **Related Issues** | TBD |
| **Dependencies** | FR-05 CRS (course ownership), FR-06 ASMT (assessment templates), FR-08 SUB (submission data), FR-14 ARCH (archive lifecycle) |

---

## 1) Scope

### In Scope
- Assignment lifecycle for teacher-created, course-scoped assignments:
  - create assignment from assessment template
  - list assignments by course
  - list assignments for user (role-aware)
  - read assignment detail
  - update assignment scheduling (`open_at`, `due_at`)
  - delete assignment (when no submissions exist)
  - archive assignment (acts as hard deadline)
- `COURSE` audience type only — assignments distribute a full assessment template to all enrolled students in a course.
- Atomic submission pre-creation for enrolled students on assignment creation.
- Scheduling: `open_at` and optional `due_at` with validation (`open_at` must precede `due_at`).
- Creator-only mutation policy: only the teacher who created the assignment can update, delete, or archive it.
- Two-tier delete policy: hard delete when no student work has been started (all submissions `NOT_STARTED`); `409 Conflict` when any submission has progressed beyond `NOT_STARTED`.
- Assignment archive lifecycle (`ACTIVE`/`ARCHIVED`): archive blocks new submissions and hides assignment from active student lists.
- Archived assessment check at creation time (enforces `ASMT-CN-13`).
- Read access matrix:
  - ADMIN/RESEARCHER: all assignments globally and cross-user listing
  - TEACHER: assignments for own courses only (course ownership from FR-05 `CRS-CN-01`)
  - STUDENT: enrolled course assignments, time-filtered (`open_at <= now` and (`due_at` is null or `due_at >= now`))

### Out of Scope
- `TEACHER` audience type for self-assessments (removed from FR-07 contract; see Deprecations).
- Question subset selection (assignments use the full assessment template).
- Grading and scoring execution (FR-08 SUB).
- Assessment template management (FR-06 ASMT).
- Bulk assignment creation.
- Wireframes and Playwright E2E scripts (tracked separately).

### Deprecations
- `TEACHER` audience type — deprecated. Still present in `models.py` (`AudienceType` enum) and `serializers.py` (validation logic). Removal target: next FR-07 implementation release.

### Core Intent
- Provide teacher-created, course-scoped assignment lifecycle with scheduling and archive support.
- Enforce atomic submission pre-creation for enrolled students on assignment creation.
- Maintain creator-only mutation policy with two-tier delete semantics based on submission progress.

---

## 2) Actors

| Role | Type | ASGN domain permissions |
|------|------|--------------------------|
| ADMIN | System role (`is_staff=True`) | Read-only visibility across all assignments; cross-user assignment listing |
| RESEARCHER | User role | Read-only visibility across all assignments; cross-user assignment listing |
| TEACHER | User role | Create/update/delete/archive own assignments; read assignments for own courses only |
| STUDENT | User role | Read assignments for enrolled courses within active time window |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER > STUDENT

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| ASGN-US-01 | TEACHER | As a teacher I can create an assignment from an assessment template for one of my courses so that enrolled students receive submissions to complete. |
| ASGN-US-02 | ADMIN, RESEARCHER, TEACHER | As a privileged user I can view assignments for a course so that I can monitor what has been assigned. |
| ASGN-US-03 | ADMIN, RESEARCHER, TEACHER, STUDENT | As any authenticated user I can view assignments relevant to me so that I know what work is available or assigned. |
| ASGN-US-04 | TEACHER | As a teacher I can extend or adjust the deadline on my assignment so that students have more time if needed. |
| ASGN-US-05 | TEACHER | As a teacher I can delete my assignment when no student work exists so that I can clean up mistakes. |
| ASGN-US-06 | TEACHER | As a teacher I can archive my assignment so that it acts as a hard deadline and no further submissions are accepted. |

---

## 4) Use Cases

### ASGN-UC-01 — Create Assignment

**Roles:** TEACHER
**Endpoint:** `POST /api/v1/assignments`

**Main Flow:**
1. Teacher submits assignment payload: `assessmentId`, `courseId`, `openAt`, optional `dueAt`.
2. System validates caller is a teacher.
3. System validates caller owns the target course (`can_manage_course` from FR-05).
4. System resolves assessment by `assessmentId`.
5. System checks assessment status is not `ARCHIVED` (enforces `ASMT-CN-13`).
6. System validates scheduling: if `dueAt` is provided, `openAt` must precede `dueAt`.
7. System creates assignment with `audience_type=COURSE`, `status=ACTIVE`, linking assessment to course.
8. System atomically pre-creates `NOT_STARTED` submissions with empty answer records for all enrolled students in the course.
9. For `MOOD_METER` assessments, submission pre-creation is skipped (students create on demand).
10. Returns assignment DTO.

**Errors:**
- `ASGN-UC-01-E1`: Missing or invalid payload.
- `ASGN-UC-01-E2`: Caller is not a teacher.
- `ASGN-UC-01-E3`: Caller does not own the target course.
- `ASGN-UC-01-E4`: Assessment not found.
- `ASGN-UC-01-E5`: Assessment is archived (enforces `ASMT-CN-13`).
- `ASGN-UC-01-E6`: `openAt` is not before `dueAt`.

**Tests (representative):**
- `test_ASGN_UC_01_TEACHER`
- `test_ASGN_CN_05_submissions_created_atomically`

---

### ASGN-UC-02 — List Assignments by Course

**Roles:** ADMIN, RESEARCHER, TEACHER
**Endpoint:** `GET /api/v1/assignments/courses/{course_id}`

**Main Flow:**
1. System resolves course by ID.
2. System validates caller has TEACHER or above role.
3. System applies course visibility:
   - ADMIN/RESEARCHER: can list assignments for any course.
   - TEACHER: can list assignments only for courses they own (`can_view_course` from FR-05).
4. System returns all assignments for the course (both `ACTIVE` and `ARCHIVED`).
5. Returns paginated assignment DTO list.

**Errors:**
- `ASGN-UC-02-E1`: Course not found.
- `ASGN-UC-02-E2`: Unauthorized role (below TEACHER).
- `ASGN-UC-02-E3`: Forbidden — teacher does not own the course.

**Tests (representative):**
- `test_ASGN_UC_02_ADMIN`
- `test_ASGN_UC_02_RESEARCHER`
- `test_ASGN_UC_02_TEACHER`

---

### ASGN-UC-03 — List Assignments for User

**Roles:** ADMIN, RESEARCHER, TEACHER, STUDENT
**Endpoint:** `GET /api/v1/assignments/users/{user_id}`

**Main Flow:**
1. System resolves user by ID.
2. System applies access control:
   - ADMIN/RESEARCHER: can list any user's assignments.
   - TEACHER/STUDENT: can only list own assignments.
3. System applies role-aware filtering:
   - STUDENT: returns `ACTIVE` assignments from enrolled courses where `open_at <= now` and (`due_at` is null or `due_at >= now`).
   - TEACHER: returns assignments created by the teacher for their own courses.
   - ADMIN/RESEARCHER viewing a STUDENT target: returns assignments from courses the student is enrolled in.
   - ADMIN/RESEARCHER viewing a TEACHER target: returns assignments the teacher created.
4. Returns paginated assignment DTO list ordered by `open_at`.

**Errors:**
- `ASGN-UC-03-E1`: User not found.
- `ASGN-UC-03-E2`: Forbidden — requesting another user's assignments without ADMIN/RESEARCHER role.

**Tests (representative):**
- `test_ASGN_UC_03_STUDENT`
- `test_ASGN_UC_03_TEACHER`
- `test_ASGN_UC_03_RESEARCHER_CROSS_USER`
- `test_ASGN_CN_08_student_time_filter`

---

### ASGN-UC-04 — Get Assignment Detail

**Roles:** ADMIN, RESEARCHER, TEACHER, STUDENT
**Endpoint:** `GET /api/v1/assignments/{assignment_id}`

**Main Flow:**
1. System resolves assignment by ID.
2. System applies access control:
   - ADMIN/RESEARCHER: can view any assignment.
   - TEACHER: can view if they own the assignment's course (`can_view_course` from FR-05).
   - STUDENT: must be enrolled in the assignment's course.
3. Returns assignment DTO.

**Errors:**
- `ASGN-UC-04-E1`: Assignment not found.
- `ASGN-UC-04-E2`: Forbidden — student not enrolled in the assignment's course.
- `ASGN-UC-04-E3`: Forbidden — teacher does not own the assignment's course.

**Tests (representative):**
- `test_ASGN_UC_04_ADMIN`
- `test_ASGN_UC_04_TEACHER`
- `test_ASGN_UC_04_STUDENT_ENROLLED`

---

### ASGN-UC-05 — Update Assignment Scheduling

**Roles:** TEACHER (creator only)
**Endpoint:** `PATCH /api/v1/assignments/{assignment_id}`

**Main Flow:**
1. System resolves assignment by ID.
2. System validates caller is the teacher who created the assignment (`created_by`).
3. System checks assignment status is `ACTIVE` (archived assignments cannot be updated).
4. System validates patch payload: only `openAt` and `dueAt` are mutable.
5. System validates scheduling: if both are provided or result from merge, `openAt` must precede `dueAt`.
6. Saves update and returns assignment DTO.

**Errors:**
- `ASGN-UC-05-E1`: Assignment not found.
- `ASGN-UC-05-E2`: Forbidden — caller is not the assignment creator.
- `ASGN-UC-05-E3`: Update blocked — assignment is archived.
- `ASGN-UC-05-E4`: Invalid scheduling (`openAt` not before `dueAt`).

**Tests (representative):**
- `test_ASGN_UC_05_TEACHER_CREATOR`

---

### ASGN-UC-06 — Delete Assignment

**Roles:** TEACHER (creator only)
**Endpoint:** `DELETE /api/v1/assignments/{assignment_id}`

**Main Flow:**
1. System resolves assignment by ID.
2. System validates caller is the teacher who created the assignment (`created_by`).
3. System checks whether any submissions have progressed beyond `NOT_STARTED`.
4. If any submission is `IN_PROGRESS`, `SUBMITTED`, or `GRADED`, request is rejected with `409 Conflict`.
5. System hard-deletes assignment and any `NOT_STARTED` submission records.
6. Returns `204 No Content`.

**Errors:**
- `ASGN-UC-06-E1`: Assignment not found.
- `ASGN-UC-06-E2`: Forbidden — caller is not the assignment creator.
- `ASGN-UC-06-E3`: Deletion blocked because student work has been started (submissions beyond `NOT_STARTED`).

**Tests (representative):**
- `test_ASGN_UC_06_TEACHER_CREATOR`
- `test_ASGN_CN_06_unreferenced_delete_succeeds`

---

### ASGN-UC-07 — Archive Assignment

**Roles:** TEACHER (creator only)
**Endpoint:** `POST /api/v1/assignments/{assignment_id}/archive`

**Main Flow:**
1. System resolves assignment by ID.
2. System validates caller is the teacher who created the assignment (`created_by`).
3. System sets assignment status to `ARCHIVED`.
4. Archived assignment is hidden from active student lists (ASGN-UC-03 student filter).
5. New submissions are blocked for this assignment (enforced by FR-08).
6. In-progress draft submissions are frozen; no further edits permitted.
7. Existing submitted/graded submissions are preserved.
8. Returns updated assignment DTO with `status: ARCHIVED`.

**Policy Requirements:**
- Archive is the recommended action when deletion is blocked by `ASGN-CN-06`.
- Once archived, an assignment can be hard-deleted only after all submissions are removed.
- Archive acts as a hard deadline: no further student interaction with the assignment.

**Errors:**
- `ASGN-UC-07-E1`: Assignment not found.
- `ASGN-UC-07-E2`: Forbidden — caller is not the assignment creator.
- `ASGN-UC-07-E3`: Assignment is already archived.

**Tests (representative):**
- `test_ASGN_UC_07_TEACHER_CREATOR`
- `test_ASGN_CN_09_archived_hides_from_student_list`
- `test_ASGN_CN_09_archived_blocks_new_submissions`

---

## 5) Constraints

### ASGN-CN-01 — Assignment Creator Ownership
- Only the teacher who created the assignment (`created_by`) can update, delete, or archive it.
- All mutating endpoints return `403 Forbidden` if the caller is not the creator.
- Applies to: ASGN-UC-05, ASGN-UC-06, ASGN-UC-07.

### ASGN-CN-02 — COURSE Audience Type Only
- Assignments use `COURSE` audience type exclusively. The assignment links a full assessment template to a specific course.
- `TEACHER` audience type is deprecated and not part of the FR-07 contract.
- Applies to: ASGN-UC-01.

### ASGN-CN-03 — Full Assessment Template
- Assignments use the complete assessment template. No question subset selection.
- Submission pre-creation generates answer records for all questions in the assessment.
- Applies to: ASGN-UC-01.

### ASGN-CN-04 — Archived Assessment Blocks Creation
- Assignment creation is rejected with `409 Conflict` when the target assessment has `status=ARCHIVED`.
- Enforces `ASMT-CN-13` from FR-06 at assignment creation time.
- Applies to: ASGN-UC-01.

### ASGN-CN-05 — Atomic Submission Provisioning
- Assignment creation and submission pre-creation for all enrolled students are wrapped in a database transaction.
- For each enrolled student: one `Submission` (status `NOT_STARTED`) and one `Answer` record per question (with type-specific extension).
- `MOOD_METER` assessments skip submission pre-creation (students create on demand).
- Applies to: ASGN-UC-01.

### ASGN-CN-06 — Deletion Blocked When Student Work Started
- Assignment deletion returns `409 Conflict` when any submission has progressed beyond `NOT_STARTED` (i.e., `IN_PROGRESS`, `SUBMITTED`, or `GRADED`).
- Hard delete is permitted when all submissions are `NOT_STARTED` (pre-created empties are cascade-deleted with the assignment).
- Applies to: ASGN-UC-06.

### ASGN-CN-07 — Scheduling Validation
- If `dueAt` is provided, `openAt` must strictly precede `dueAt`.
- Violation returns `400 Bad Request`.
- Applies to: ASGN-UC-01, ASGN-UC-05.

### ASGN-CN-08 — Student Time-Filtered Visibility
- Students see only `ACTIVE` assignments from enrolled courses where:
  - `open_at <= now`, AND
  - `due_at` is null OR `due_at >= now`.
- Archived assignments are excluded from student lists.
- Applies to: ASGN-UC-03.

### ASGN-CN-09 — Assignment Archive Lifecycle
- Assignments gain a `status` field with values `ACTIVE` (default) and `ARCHIVED`.
- Archived assignments:
  - Are hidden from active student lists (`ASGN-CN-08`).
  - Block new submissions (enforced by FR-08 SUB at submission time).
  - Block in-progress draft edits (submissions are frozen).
  - Cannot be updated (`ASGN-UC-05` rejects with `409`).
  - Remain readable by ADMIN, RESEARCHER, and TEACHER.
  - Can be hard-deleted via `ASGN-UC-06` once all submissions are removed.
- Archive is the recommended resolution when `ASGN-CN-06` blocks deletion.
- Applies to: ASGN-UC-03, ASGN-UC-05, ASGN-UC-06, ASGN-UC-07.

### ASGN-CN-10 — Course Ownership Gate on Creation
- Assignment creation requires the caller to own the target course (`can_manage_course` from FR-05 `CRS-CN-01`).
- Prevents teachers from assigning assessments to courses they do not own.
- Applies to: ASGN-UC-01.

### ASGN-CN-11 — TEACHER Audience Type Deprecated
- `TEACHER` value in `AudienceType` enum is deprecated.
- Still present in `models.py` and `serializers.py`; removal target: next FR-07 implementation release.
- Assignment creation must reject `audienceType=TEACHER` with `400 Bad Request`.
- Applies to: ASGN-UC-01.

---

## 6) Infrastructure Contract

### 6.1 Endpoint Contract

| Method | Path | Auth | UC |
|--------|------|------|-----|
| POST | `/api/v1/assignments` | IsTeacher + course ownership gate | ASGN-UC-01 |
| GET | `/api/v1/assignments/courses/{course_id}` | IsTeacherOrAbove + course visibility gate | ASGN-UC-02 |
| GET | `/api/v1/assignments/users/{user_id}` | IsAuthenticated | ASGN-UC-03 |
| GET | `/api/v1/assignments/{assignment_id}` | IsAuthenticated + enrollment/ownership gate | ASGN-UC-04 |
| PATCH | `/api/v1/assignments/{assignment_id}` | IsTeacher + creator gate | ASGN-UC-05 |
| DELETE | `/api/v1/assignments/{assignment_id}` | IsTeacher + creator gate | ASGN-UC-06 |
| POST | `/api/v1/assignments/{assignment_id}/archive` | IsTeacher + creator gate | ASGN-UC-07 |

> **Trailing-slash note:** Django framework may accept trailing-slash variants (e.g., `/api/v1/assignments/`). Canonical paths in this contract omit the trailing slash.

**Deprecations (not part of target FR-07 contract):**
- `TEACHER` audience type in `AudienceType` enum.
- Deprecation policy: deprecated now; remove from `models.py` and `serializers.py` in the next FR-07 implementation release.

---

## 7) Error Model

Standard error payload:
- `{"detail": "<message>"}` for validation, not-found, or authorization errors.

Expected statuses by UC:
- `400`: invalid payload/scheduling violation/deprecated audience type
- `403`: forbidden by role or creator ownership
- `404`: assignment/course/user not found
- `409`: mutation blocked by submission references (`ASGN-UC-06-E3`), archived assessment (`ASGN-UC-01-E5`), or already archived (`ASGN-UC-07-E3`, `ASGN-UC-05-E3`)
- `201`: create success
- `200`: read/update success
- `204`: delete success

---

## 8) Test Strategy by Layer

### Backend Unit
- Creator ownership enforcement on mutation paths.
- Scheduling validation (`openAt` before `dueAt`).
- Student time-filtered visibility logic.
- Submission pre-creation for all enrolled students.
- Mood meter submission skip behavior.
- Archive lifecycle state transitions.

### Backend Integration
- Route + auth + serializer + persistence:
  - `tests/integration/test_assignments_routes.py`
  - `tests/integration/test_assignments_errors.py`
  - additional FR-07 traceability tests for ASGN-CN-01/04/05/06/07/08/09/11

### Frontend Unit/Integration
- Deferred for FR-07 UI implementation phase; backend contract is source of truth for now.

### System Tests (Black Box)
- `ST-ASGN-UC-01` through `ST-ASGN-UC-07`
- Required constraint checks:
  - `ST-ASGN-CN-01` (creator-only mutation)
  - `ST-ASGN-CN-04` (archived assessment blocks creation)
  - `ST-ASGN-CN-05` (atomic submission provisioning)
  - `ST-ASGN-CN-06` (delete blocked when submissions exist)
  - `ST-ASGN-CN-08` (student time-filtered visibility)
  - `ST-ASGN-CN-09` (archive hides from students, blocks submissions and drafts)

---

## 9) NFR Cross-References

- **NFR-Security**
  - Role gates enforced server-side (`IsTeacherOrAbove` with creator mutation gate, `IsAuthenticated` for student read).
  - Creator ownership checked on all mutation paths.
  - Student enrollment verified before assignment detail access.
- **NFR-Reliability**
  - Submission provisioning and assignment creation are transactional.
  - Deterministic status codes and error payloads.
  - Mutation blocked when downstream data integrity would be compromised.
- **NFR-Performance**
  - Paginated assignment listing by course and by user.
  - Student time-filtered queries avoid unbounded response payloads.
- **NFR-Maintainability**
  - Assignment domain behavior centralized in service layer (`assignments/services/`).
  - Creator ownership pattern consistent with FR-05 course ownership.
  - Archive lifecycle consistent with FR-06 assessment archive pattern.

---

## 10) Cross-Domain References

| Domain | ASGN dependency | Integration note |
|--------|-----------------|------------------|
| FR-05 CRS | Course ownership gate on creation | ASGN-CN-10 requires `can_manage_course` from CRS-CN-01 for assignment creation |
| FR-06 ASMT | Assessment template source | Assignments reference assessment templates; archived assessment check enforces ASMT-CN-13 |
| FR-08 SUB | Submission pre-creation and lifecycle | ASGN-CN-05 atomic submission provisioning; ASGN-CN-06 blocks delete when submissions progressed |
| FR-09 VIZ | Visualization aggregates per assignment | VIZ-UC-03 computes grade distribution from assignment submissions |
| FR-14 ARCH | Assignment archive lifecycle | ARCH-UC-02 archives assignments; blocks new submissions and draft edits |

---

## 11) Current Implementation Alignment Notes

This draft defines the target FR-07 contract. Current code has known deltas that must be resolved before FR-07 can be marked COMPLETE:

1. Add creator ownership check on delete path; current code allows any teacher to delete any assignment (ASGN-CN-01).
2. Add `PATCH /api/v1/assignments/{assignment_id}` endpoint for scheduling updates (ASGN-UC-05). Endpoint does not exist in current code.
3. Add `POST /api/v1/assignments/{assignment_id}/archive` endpoint (ASGN-UC-07). Endpoint does not exist in current code.
4. Add `status` field (`ACTIVE`/`ARCHIVED`) to Assignment model (ASGN-CN-09).
5. Add archived assessment check at assignment creation time; reject with `409` if assessment `status=ARCHIVED` (ASGN-CN-04).
6. Add scheduling validation (`openAt` before `dueAt`) on create and update paths (ASGN-CN-07).
7. Change delete service to check submission status instead of cascade-deleting; reject with `409` when any submission is beyond `NOT_STARTED`, allow cascade-delete of `NOT_STARTED` submissions (ASGN-CN-06).
8. Reject `audienceType=TEACHER` at assignment creation with `400`; deprecate `TEACHER` value in `AudienceType` enum in `models.py` and `serializers.py` (ASGN-CN-11).
9. Add course ownership check at assignment creation (`can_manage_course` from FR-05); current code uses `IsTeacher` without verifying course ownership (ASGN-CN-10).
10. Add course ownership/visibility gate on list-by-course and detail endpoints for teachers; current code allows any teacher to view any assignment regardless of course ownership (ASGN-UC-02, ASGN-UC-04).
11. Align permission class on create endpoint: current code uses `IsTeacher`; contract specifies `IsTeacher + course ownership gate` — add in-view course ownership check (ASGN-CN-10).
12. Add missing FR-07 traceability tests for constraints and error paths.
13. Preserve paginated listing behavior on assignment list endpoints during FR-07 changes.
