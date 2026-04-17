# FR-08 Submissions (SUB) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | SUB |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER, STUDENT |
| **Related Issues** | TBD |
| **Dependencies** | FR-05 CRS (course enrollment), FR-06 ATMPL (assignment template/question types), FR-07 ASGN (assignment lifecycle and archive), FR-14 ARCH (archive status gates) |

---

## 1) Scope

### In Scope
- Submission lifecycle for pre-created student submissions:
  - save draft (partial answers, `IN_PROGRESS`)
  - submit final answers (`SUBMITTED` → auto-grade if applicable → `GRADED`)
  - manual grading by teacher/admin (`GRADED`)
- 3 answer types matching assignment template question types: `MULTIPLE_CHOICE`, `SHORT_ANSWER`, `NUMBER_SCALE`.
- Auto-grading on submit for non-MANUAL grading modes:
  - `MULTIPLE_CHOICE`: sum `McqChoice.points` for selected indices.
  - `NUMBER_SCALE`: exact-match against `target` for full `max_points`.
  - `SHORT_ANSWER`: skip (not auto-gradable).
- Manual grading: positional score array with per-grading-mode answer targeting.
- Read access matrix:
  - ADMIN/RESEARCHER: all submissions globally.
  - TEACHER: submissions for own assignments only (assignment ownership gate).
  - STUDENT: own submissions only.
- ~~Mood meter on-demand submission creation~~ (removed; MOOD_METER question type no longer supported).
- Assignment archive enforcement: block new submissions and freeze drafts (enforces `ASGN-CN-09` from FR-07).

### Out of Scope
- Submission pre-creation at assignment time (FR-07 `ASGN-CN-05`).
- AssignmentTemplate template management (FR-06 ATMPL).
- Assignment lifecycle (FR-07 ASGN).
- Visualization and analytics dashboards (FR-09 VIZ).
- Paper submission upload (not in current system).
- Due-date enforcement at submission time (`due_at` is a visibility filter in FR-07 `ASGN-CN-08`, not a submission blocker; archive is the hard deadline mechanism).
- Bulk grading across multiple submissions.
- UI wireframes and future browser smoke flows (tracked separately).

### Core Intent
- Manage submission lifecycle from pre-creation through draft, submit, and grading with role-appropriate access controls.
- Support auto-grading on submit for eligible question types with hybrid grading mode for mixed assignment templates.
- Enforce archive-based hard deadline semantics and student self-access restrictions across all submission operations.

### Deprecations
- Teacher self-assignment template flow: `teacher_self_assess` view function is implemented but not wired to any URL pattern (dead code). `GET /api/v1/teachers/{teacher_id}/submissions` is a legacy endpoint with no active write path — the corresponding create route was never wired. Related to deprecated `TEACHER` audience type from FR-07 (`ASGN-CN-11`). Removal target: next FR-08 implementation release.
- Generic edit endpoint: `PATCH /api/v1/submissions/` overlaps with SUB-UC-01 (save draft) and SUB-UC-02 (submit). Rationalization target: next FR-08 implementation release.

---

## 2) Actors

| Role | Type | SUB domain permissions |
|------|------|-------------------------|
| ADMIN | System role (`is_staff=True`) | Read-only visibility across all submissions; manual grading override |
| RESEARCHER | User role | Read-only visibility across all submissions |
| TEACHER | User role | Read/grade submissions for own assignments |
| STUDENT | User role | Save draft, submit, view own submissions |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER > STUDENT

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| SUB-US-01 | STUDENT | As a student I can save my progress on an assignment so that I can return and finish later. |
| SUB-US-02 | STUDENT | As a student I can submit my completed answers to an assignment so that my teacher can review and grade my work. |
| SUB-US-03 | TEACHER, ADMIN | As a teacher or admin I can manually grade a student's submission by assigning scores to each answer so that the student receives a grade. |
| SUB-US-04 | ADMIN, RESEARCHER, TEACHER, STUDENT | As any authenticated user I can view a submission's detail including answers and scores so that I can review the work. |
| SUB-US-05 | ADMIN, RESEARCHER, TEACHER | As a privileged user I can view all submissions for an assignment so that I can monitor class progress. |
| SUB-US-06 | ADMIN, RESEARCHER, TEACHER, STUDENT | As any authenticated user I can view submissions relevant to me so that I can track progress and grades. |

---

## 4) Use Cases

### SUB-UC-01 — Save Draft

**Roles:** STUDENT
**Endpoint:** `PATCH /api/v1/students/{student_id}/assignments/{assignment_id}/draft`

**Main Flow:**
1. Student submits partial answers payload: `answers` array.
2. System validates caller is a student.
3. System validates caller's user ID matches the URL `student_id` parameter (self-only).
4. System resolves assignment by `assignment_id`.
5. System checks assignment status is `ACTIVE` (not `ARCHIVED`; enforces `SUB-CN-07`).
6. System validates caller is enrolled in the assignment's course.
7. System finds existing pre-created submission for this student + assignment. If none exists (e.g., late enrollment), system creates one.
8. System replaces all existing answers with the submitted answers (full replacement per `SUB-CN-10`).
9. System sets submission status to `IN_PROGRESS`.
10. Returns updated submission DTO.

**Errors:**
- `SUB-UC-01-E1`: Missing or invalid answer payload.
- `SUB-UC-01-E2`: Caller is not a student.
- `SUB-UC-01-E3`: Student ID mismatch (caller ≠ URL `student_id`).
- `SUB-UC-01-E4`: Assignment not found.
- `SUB-UC-01-E5`: Assignment is archived (draft frozen per `SUB-CN-07`).
- `SUB-UC-01-E6`: Student not enrolled in the assignment's course.

**Tests (representative):**
- `test_SUB_UC_01_STUDENT`

---

### SUB-UC-02 — Submit Assignment

**Roles:** STUDENT
**Endpoint:** `POST /api/v1/assignments/{assignment_id}/submissions`

**Main Flow:**
1. Student submits final answers payload: `answers` array.
2. System validates caller is a student.
3. System resolves assignment by `assignment_id`.
4. System checks assignment status is `ACTIVE` (not `ARCHIVED`; enforces `SUB-CN-06`).
5. System validates caller is enrolled in the assignment's course.
6. System finds existing pre-created submission for this student + assignment.
7. System replaces all existing answers with the submitted answers (full replacement per `SUB-CN-10`).
9. System sets submission status to `SUBMITTED` and `submitted_at` to current timestamp.
10. System resolves the assignment template linked to the assignment.
11. If grading mode is not `MANUAL`: system runs auto-grading (`SUB-CN-03`).
    - `AUTO`: status → `GRADED`, score calculated.
    - `HYBRID`: status remains `SUBMITTED`, auto-gradable answers scored, awaits manual grading for `SHORT_ANSWER` answers.
12. Returns submission DTO with status and score.

**Errors:**
- `SUB-UC-02-E1`: Missing or invalid answer payload.
- `SUB-UC-02-E2`: Caller is not a student.
- `SUB-UC-02-E3`: Assignment not found.
- `SUB-UC-02-E4`: Assignment is archived (new submissions blocked per `SUB-CN-06`).
- `SUB-UC-02-E5`: Student not enrolled in the assignment's course.

**Tests (representative):**
- `test_SUB_UC_02_STUDENT`

---

### SUB-UC-03 — Grade Submission

**Roles:** TEACHER, ADMIN
**Endpoint:** `PATCH /api/v1/submissions/{submission_id}/override-score`

**Main Flow:**
1. Caller submits score override payload: positional array of numeric scores (one per answer).
2. System validates caller is a teacher or admin.
3. System resolves submission by `submission_id`.
4. System validates caller owns the assignment associated with the submission (`SUB-CN-08`).
   - ADMIN: bypasses ownership check.
5. System resolves the assignment template linked to the submission's assignment.
6. System applies scores based on grading mode:
   - `HYBRID`: apply scores only to `SHORT_ANSWER` answers; preserve existing auto-scores for `MULTIPLE_CHOICE` and `NUMBER_SCALE`.
   - `MANUAL` / other: apply scores to all answers in positional order.
7. If score array has more entries than answers, the extra entry is added as bonus to total.
8. System calculates total submission score (sum of all answer scores + bonus).
9. System sets submission status to `GRADED` and `submitted_at` if null.
10. Returns updated submission DTO.

**Errors:**
- `SUB-UC-03-E1`: Missing or invalid score payload.
- `SUB-UC-03-E2`: Caller is not a teacher or admin.
- `SUB-UC-03-E3`: Submission not found.
- `SUB-UC-03-E4`: Forbidden — teacher does not own the assignment.

**Tests (representative):**
- `test_SUB_UC_03_TEACHER`
- `test_SUB_UC_03_ADMIN`

---

### SUB-UC-04 — Get Submission Detail

**Roles:** ADMIN, RESEARCHER, TEACHER, STUDENT
**Endpoint:** `GET /api/v1/submissions/{submission_id}`

**Main Flow:**
1. System resolves submission by `submission_id`.
2. System applies access control:
   - ADMIN: can view any submission.
   - RESEARCHER: can view any submission (read-only).
   - TEACHER: can view if they own the submission's assignment (`SUB-CN-08`).
   - STUDENT: can view only own submissions (`submission.student_id == user.id`).
3. Returns full submission DTO with all answers and scores.

**Errors:**
- `SUB-UC-04-E1`: Submission not found.
- `SUB-UC-04-E2`: Forbidden — student not the submission owner.
- `SUB-UC-04-E3`: Forbidden — teacher does not own the assignment.

**Tests (representative):**
- `test_SUB_UC_04_ADMIN`
- `test_SUB_UC_04_RESEARCHER`
- `test_SUB_UC_04_TEACHER`
- `test_SUB_UC_04_STUDENT`

---

### SUB-UC-05 — Get Student Assignment Submission

**Roles:** ADMIN, RESEARCHER, TEACHER, STUDENT
**Endpoint:** `GET /api/v1/students/{student_id}/assignments/{assignment_id}/submission`

**Main Flow:**
1. System resolves student by `student_id` and assignment by `assignment_id`.
2. System applies access control:
   - ADMIN/RESEARCHER: can view any student's submission for any assignment.
   - TEACHER: can view if they own the assignment's course.
   - STUDENT: can view only own submission (`student_id == user.id`).
3. System looks up submission by student + assignment composite key.
4. Returns full submission DTO with all answers and scores.

**Errors:**
- `SUB-UC-05-E1`: Student or assignment not found.
- `SUB-UC-05-E2`: Submission not found for this student + assignment combination.
- `SUB-UC-05-E3`: Forbidden — student requesting another student's submission.
- `SUB-UC-05-E4`: Forbidden — teacher does not own the assignment's course.

**Tests (representative):**
- `test_SUB_UC_05_ADMIN`
- `test_SUB_UC_05_TEACHER`
- `test_SUB_UC_05_STUDENT`
- `test_SUB_UC_05_RESEARCHER`

---

### SUB-UC-06 — List Submissions by Assignment

**Roles:** ADMIN, RESEARCHER, TEACHER
**Endpoint:** `GET /api/v1/assignments/{assignment_id}/submissions`

**Main Flow:**
1. System resolves assignment by `assignment_id`.
2. System validates caller has TEACHER or above role.
3. System applies assignment visibility:
   - ADMIN/RESEARCHER: can list submissions for any assignment.
   - TEACHER: can list submissions only for assignments they own (`SUB-CN-08`).
4. System returns all submissions for the assignment (all statuses).
5. Returns paginated submission compact DTO list (no answer payload).

**Errors:**
- `SUB-UC-06-E1`: Assignment not found.
- `SUB-UC-06-E2`: Unauthorized role (STUDENT cannot list by assignment).
- `SUB-UC-06-E3`: Forbidden — teacher does not own the assignment.

**Tests (representative):**
- `test_SUB_UC_06_ADMIN`
- `test_SUB_UC_06_RESEARCHER`
- `test_SUB_UC_06_TEACHER`

---

### SUB-UC-07 — List Student Submissions

**Roles:** ADMIN, RESEARCHER, TEACHER, STUDENT
**Endpoint:** `GET /api/v1/students/{student_id}/submissions`

**Main Flow:**
1. System resolves student by `student_id`.
2. System applies access control:
   - ADMIN/RESEARCHER: can list any student's submissions.
   - TEACHER: can list submissions for students in courses they own.
   - STUDENT: can list only own submissions (`student_id == user.id`).
3. Returns paginated submission compact DTO list (no answer payload).

**Errors:**
- `SUB-UC-07-E1`: Student not found.
- `SUB-UC-07-E2`: Forbidden — requesting another student's submissions without sufficient privileges.

**Tests (representative):**
- `test_SUB_UC_07_ADMIN`
- `test_SUB_UC_07_TEACHER`
- `test_SUB_UC_07_STUDENT`

---

### SUB-UC-08 — List My Submissions

**Roles:** ADMIN, RESEARCHER, TEACHER, STUDENT
**Endpoint:** `GET /api/v1/submissions/me`

**Main Flow:**
1. System resolves caller identity from the authenticated session.
2. System queries submissions tied to the caller identity.
4. Optional `status` query filter (`NOT_STARTED`, `IN_PROGRESS`, `SUBMITTED`, `GRADED`).
5. Returns paginated submission compact DTO list ordered by `submitted_at` descending (undated drafts last).

**Errors:**
- No domain-specific errors beyond standard authentication/authorization handling.

**Tests (representative):**
- `test_SUB_UC_08_STUDENT`
- `test_SUB_UC_08_ADMIN`
- `test_SUB_UC_08_status_filter`

---

## 5) Constraints

### SUB-CN-01 — Submission Status Lifecycle
- Submissions progress through: `NOT_STARTED → IN_PROGRESS → SUBMITTED → GRADED`.
- `NOT_STARTED`: pre-created by assignment creation (`ASGN-CN-05`); no student interaction yet.
- `IN_PROGRESS`: student has saved a draft via SUB-UC-01.
- `SUBMITTED`: student has finalized answers via SUB-UC-02; auto-grading may have run.
- `GRADED`: all answers scored (auto or manual) via SUB-UC-02 auto-grade or SUB-UC-03 manual grade.
- State transitions are enforced by service-layer validation.
- Applies to: SUB-UC-01, SUB-UC-02, SUB-UC-03.

### SUB-CN-02 — Student Submission Access Control
- Students can only access submissions where `submission.student_id == user.id`.
- Student submission write operations (draft save, final submit) require enrollment in the assignment's course.
- Students cannot view other students' submissions even with a known submission ID.
- Applies to: all SUB UCs involving STUDENT role.

### SUB-CN-03 — Auto-Grading on Submit
- When a submission is submitted (status → `SUBMITTED`) and the assignment template's grading mode is not `MANUAL`:
  - `MULTIPLE_CHOICE`: sum `McqChoice.points` for selected choice indices via `_auto_score_mcq()`.
  - `NUMBER_SCALE`: if `answer.val == question.target`, award `max_points`; else 0, via `_auto_score_number_scale()`.
  - `SHORT_ANSWER`: skip (not auto-gradable).
- `AUTO` grading mode: status → `GRADED`, `submitted_at` set.
- `HYBRID` grading mode: status remains `SUBMITTED`, auto-gradable answers scored, awaits manual scoring of `SHORT_ANSWER` answers via SUB-UC-03.
- Auto-grading executes synchronously within the submission request transaction.
- Applies to: SUB-UC-02.

### SUB-CN-04 — Mood Meter On-Demand Submissions
- ~~`MOOD_METER` assignment templates skip submission pre-creation~~ (removed; MOOD_METER no longer supported).
- No mood meter submission behavior is part of the active FR-08 contract.
- Applies to: SUB-UC-02.

### SUB-CN-05 — Score Calculation
- Total submission score = sum of all answer-level scores.
- For manual grading (SUB-UC-03), scores are applied positionally: `scores[i]` maps to `answers[i]` in order.
- `HYBRID` mode: manual scores apply only to `SHORT_ANSWER` answers; auto-scored answers (`MULTIPLE_CHOICE`, `NUMBER_SCALE`) preserve their auto-calculated scores.
- If the score array has more entries than answers, the extra entry is added as bonus to the total.
- Per-answer score overrides are validated so score cannot exceed each question's `max_points`.
- Applies to: SUB-UC-02, SUB-UC-03.

### SUB-CN-06 — Archived Assignment Blocks Submissions
- When an assignment has `status=ARCHIVED`, new submissions via SUB-UC-02 are rejected with `409 Conflict`.
- Enforces `ASGN-CN-09` from FR-07 ("Block new submissions").
- Applies to: SUB-UC-02.

### SUB-CN-07 — Frozen Drafts on Archive
- When an assignment has `status=ARCHIVED`, draft saves via SUB-UC-01 are rejected with `409 Conflict`.
- Enforces `ASGN-CN-09` from FR-07 ("Block in-progress draft edits; submissions are frozen").
- Applies to: SUB-UC-01.

### SUB-CN-08 — Teacher Assignment Ownership Gate
- Teachers can only access submissions for assignments they own.
- Ownership verified via `assignment.course` ownership from FR-05 (`CRS-CN-01`) or `assignment.created_by` match from FR-07 (`ASGN-CN-01`).
- ADMIN and RESEARCHER bypass this check (read-only for RESEARCHER).
- Applies to: SUB-UC-03, SUB-UC-04, SUB-UC-05, SUB-UC-06, SUB-UC-07.

### SUB-CN-09 — Answer Type Enumeration
- Supported answer types: `MULTIPLE_CHOICE`, `SHORT_ANSWER`, `NUMBER_SCALE`.
- Each answer type uses a OneToOne extension model matching the corresponding question type from FR-06:
  - `MultipleChoiceAnswer` → `MultipleChoiceSelected` entries (0-based choice indices).
  - `ShortAnswerAnswer` → `text` field (student's text response).
  - `NumberScaleAnswer` → `val` field (student's selected numeric value).
  - `MoodMeterAnswer` → `row` (energy axis) and `col` (pleasantness axis) fields.
- Answer type must match the question type from the assignment template.
- Applies to: SUB-UC-01, SUB-UC-02.

### SUB-CN-10 — Answer Replacement Semantics
- Draft saves (SUB-UC-01) and final submissions (SUB-UC-02) replace all existing answers (full replacement, not merge).
- Old answers and their type-specific extensions are deleted; new answers are created.
- This ensures answer state is always consistent with the latest student input.
- Analogous to `ATMPL-CN-08` (question replacement semantics) from FR-06.
- Applies to: SUB-UC-01, SUB-UC-02.

### SUB-CN-11 — Teacher Self-AssignmentTemplate Legacy Dead Path
- `teacher_self_assess` view function is implemented in `submissions/views.py` but was never wired to any URL pattern (dead code).
- `GET /api/v1/teachers/{teacher_id}/submissions` is a legacy read endpoint whose corresponding write route was never activated.
- Related to deprecated `TEACHER` audience type from FR-07 (`ASGN-CN-11`).
- Removal target: next FR-08 implementation release.
- Applies to: endpoint contract (legacy/dead paths section).

---

## 6) Infrastructure Contract

### 6.1 Endpoint Contract

| Method | Path | Auth | UC |
|--------|------|------|-----|
| PATCH | `/api/v1/students/{student_id}/assignments/{assignment_id}/draft` | IsAuthenticated + student self + enrollment gate | SUB-UC-01 |
| POST | `/api/v1/assignments/{assignment_id}/submissions` | IsAuthenticated + student role + enrollment gate | SUB-UC-02 |
| GET | `/api/v1/assignments/{assignment_id}/submissions` | IsAuthenticated + assignment visibility gate | SUB-UC-06 |
| GET | `/api/v1/submissions/{submission_id}` | IsAuthenticated + submission access gate | SUB-UC-04 |
| GET | `/api/v1/submissions/me` | IsAuthenticated + self scope | SUB-UC-08 |
| PATCH | `/api/v1/submissions/{submission_id}/override-score` | IsAuthenticated + grading access gate | SUB-UC-03 |
| GET | `/api/v1/students/{student_id}/submissions` | IsAuthenticated + self/ownership gate | SUB-UC-07 |
| GET | `/api/v1/students/{student_id}/assignments/{assignment_id}/submission` | IsAuthenticated + self/ownership gate | SUB-UC-05 |

> **Trailing-slash note:** Django framework may accept trailing-slash variants. Canonical paths in this contract omit the trailing slash.

**Legacy / dead paths (not part of target FR-08 contract):**
- `GET /api/v1/teachers/{teacher_id}/submissions` — legacy read path for teacher self-assignment templates; corresponding write route (`teacher_self_assess`) was never wired to any URL.
- `PATCH /api/v1/submissions/` — generic edit endpoint; overlaps with SUB-UC-01 and SUB-UC-02.
- Removal policy: remove in the next FR-08 implementation release.

---

## 7) Error Model

Standard error payload:
- `{"detail": "<message>"}` for validation, not-found, or authorization errors.

Expected statuses by UC:
- `400`: invalid payload, missing required params
- `403`: forbidden by role, ownership, enrollment, or self-only check
- `404`: submission, assignment, or student not found
- `409`: submission/draft blocked by archived assignment (`SUB-UC-01-E5`, `SUB-UC-02-E4`)
- `200`: read/update/grade success
- `201`: submit success (new submission created)

---

## 8) Test Strategy by Layer

### Backend Unit
- Submission status transitions and lifecycle.
- Auto-grading logic per answer type (`_auto_score_mcq`, `_auto_score_number_scale`).
- Score calculation (total, hybrid mode, bonus).
- Answer replacement semantics (delete + re-create).
- DTO conversion for all answer types.

### Backend Integration
- Route + auth + serializer + persistence:
  - `tests/integration/test_submissions_routes.py`
  - `tests/integration/test_submissions_errors.py`
  - additional FR-08 traceability tests for SUB-CN-01/02/03/04/05/06/07/08

### Frontend Unit/Integration
- Deferred for FR-08 UI implementation phase; backend contract is source of truth for now.

### System Tests (Black Box)
- `ST-SUB-UC-01` through `ST-SUB-UC-08`
- Required constraint checks:
  - `ST-SUB-CN-01` (status lifecycle transitions)
  - `ST-SUB-CN-02` (student own-submission access only)
  - `ST-SUB-CN-03` (auto-grading on submit)
  - `ST-SUB-CN-06` (archived assignment blocks submissions)
  - `ST-SUB-CN-07` (frozen drafts on archive)
  - `ST-SUB-CN-08` (teacher assignment ownership for grading)

---

## 9) NFR Cross-References

- **NFR-Security**
  - Role gates enforced server-side (`IsAuthenticated` with per-role access checks in views).
  - Student restricted to own submissions across all endpoints.
  - Teacher ownership verified on all grading and read paths.
  - Enrollment required for student write operations.
- **NFR-Reliability**
  - Auto-grading executes synchronously within submission transaction.
  - Deterministic status codes and error payloads.
  - Answer replacement is atomic (delete + re-create in same transaction).
- **NFR-Performance**
  - Paginated submission listing by assignment and by student.
  - Compact DTO for list views (no answer payload).
  - Auto-grading is synchronous; large assignment templates may warrant future async optimization.
- **NFR-Maintainability**
  - Submission domain behavior centralized in service layer (`submissions/services.py`).
  - Answer type extensions use consistent OneToOne pattern matching question types from FR-06.
  - Teacher ownership pattern consistent with FR-07 assignment creator ownership.
  - Archive enforcement pattern consistent with FR-06/FR-07 archive lifecycle.

---

## 10) Cross-Domain References

| Domain | SUB dependency | Integration note |
|--------|----------------|------------------|
| FR-05 CRS | Course enrollment for submission access | Student must be enrolled in assignment's course for write operations (SUB-CN-02) |
| FR-06 ATMPL | AssignmentTemplate question types and grading modes | Answer types match question types from ATMPL; grading mode determines auto-grade behavior (SUB-CN-03) |
| FR-07 ASGN | Assignment lifecycle and archive gates | Submission pre-creation at assignment time (ASGN-CN-05); archive blocks writes (SUB-CN-06, SUB-CN-07) |
| FR-09 VIZ | Visualization data source | VIZ aggregates computed from submission records and status values |
| FR-10 EXP | Export data source | EXP exports submission-level data including answers and scores |
| FR-14 ARCH | Archive status gates | Archived assignments block new submissions and freeze drafts |
| FR-15 IMG | Image attachments | IMG-UC-01..04 attach images to submissions; post-submit lock shared with SUB status |

---

## 11) Current Implementation Alignment Notes

Current implementation is aligned with the FR-08 target contract for submission lifecycle, archive gates, ownership checks, and compact paginated list behavior.

Open improvements (non-blocking):
1. `SUB-UC-03`: HYBRID manual grading remains positional in override payloads; answer-keyed patch payloads would improve teacher UX.
2. Dedicated frontend list/report pages for SUB-UC-06/07/08 can continue as iterative UI work.
