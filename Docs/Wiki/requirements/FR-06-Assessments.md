# FR-06 Assessments (ASMT) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | ASMT |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER |
| **Related Issues** | TBD |
| **Dependencies** | FR-07 ASGN (assignment references), FR-08 SUB (submission data), FR-14 ARCH (archive lifecycle) |

---

## 1) Scope

### In Scope
- Assessment template lifecycle for researcher-authored templates:
  - create assessment with questions
  - list available assessments
  - read assessment detail
  - update assessment (when unreferenced by assignments)
  - delete assessment (when unreferenced by assignments)
- 4 question types (current backend): `MULTIPLE_CHOICE`, `SHORT_ANSWER`, `NUMBER_SCALE`, `MOOD_METER`.
- Grading modes in active backend contract: `AUTO`, `MANUAL`, `HYBRID`, `MOOD_METER`, with `RUBRIC` accepted as an input compatibility alias that persists as `MANUAL`.
- Rubric linkage/lifecycle within assessment domain (assessment-linked `rubric` FK + `rubric_assessment_ids`).
- Authorization matrix:
  - RESEARCHER/ADMIN: full CRUD
  - TEACHER: read-only visibility
  - STUDENT: no ASMT domain access
- Two-tier mutation policy: unreferenced assessments allow update/delete; referenced assessments return `409 Conflict`.
- Assessment archive lifecycle: referenced assessments can be archived to prevent new assignment creation while preserving existing assignments.
- Auto-grading detection per question type.
- Atomic question provisioning within assessment create/update.

### Out of Scope
- Student assessment access (students interact through assignments/submissions in FR-07/FR-08 only).
- Assignment creation from assessment templates (FR-07 ASGN).
- Submission, answer, and grading flows (FR-08 SUB).
- Assessment subset selection for assignments (FR-07 decision).
- Rubric as a standalone entity (current model uses assessment-linked fields; standalone rubric entity is a future architectural decision).
- Future question types: `TRUE_FALSE`, `REFLECTION` (planned extensions; not in current backend contract).
- UI wireframes and future browser smoke flows (tracked separately).

### Deprecations
- `POST /api/v1/assessments/{assessment_id}/teacher-self-assess` — deprecated. Route still exists in codebase; removal target: next FR-06 implementation release.

### Core Intent
- Provide researcher-authored assessment templates with multi-type question support and grading mode configuration.
- Enforce two-tier mutation policy: unreferenced assessments allow full CRUD; referenced assessments are protected from destructive changes.
- Support assessment archive lifecycle to retire templates without breaking existing assignments.

---

## 2) Actors

| Role | Type | ASMT domain permissions |
|------|------|--------------------------|
| ADMIN | System role (`is_staff=True`) | Full CRUD on assessment templates; same permissions as RESEARCHER |
| RESEARCHER | User role | Full CRUD on assessment templates; primary assessment author |
| TEACHER | User role | Read-only visibility across all assessment templates |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER

> **Note:** STUDENT has no ASMT domain access. Students see assessment content only through assignments (FR-07) and submissions (FR-08).

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| ASMT-US-01 | RESEARCHER, ADMIN | As a researcher or admin I can create an assessment template with questions so that teachers can assign it to their courses. |
| ASMT-US-02 | ADMIN, RESEARCHER, TEACHER | As an admin, researcher, or teacher I can view available assessment templates so that I can review content or select templates for assignment. |
| ASMT-US-03 | RESEARCHER, ADMIN | As a researcher or admin I can update an assessment template that has no assignments so that I can correct or improve questions before distribution. |
| ASMT-US-04 | RESEARCHER, ADMIN | As a researcher or admin I can delete an unused assessment template so that the template library stays clean. |
| ASMT-US-05 | RESEARCHER, ADMIN | As a researcher or admin I can link a rubric to an assessment so that grading criteria are attached to the template. |
| ASMT-US-06 | RESEARCHER, ADMIN | As a researcher or admin I can archive a referenced assessment so that no new assignments are created from it while existing assignments remain valid. |

---

## 4) Use Cases

### ASMT-UC-01 — Create Assessment

**Roles:** RESEARCHER, ADMIN
**Endpoint:** `POST /api/v1/assessments`

**Main Flow:**
1. Caller submits assessment payload: `title`, optional `category`, `gradingMode`, `questions` array, optional `rubricId`, optional `rubricAssessmentIds`.
2. System validates caller has RESEARCHER or ADMIN role.
3. System validates `gradingMode` against supported enum.
4. If `gradingMode` is `MOOD_METER`, system delegates to mood meter auto-configuration (single pre-set question, `maxPoints=0`, `graded=false`).
5. For each question in the `questions` array:
   - System validates `type` against supported question kind enum.
   - System creates base `Question` record and type-specific extension model.
   - System determines `autoGradable` flag: `true` for `MULTIPLE_CHOICE` and `NUMBER_SCALE`; `false` for `SHORT_ANSWER` and `MOOD_METER`.
6. If `rubricId` is provided, system applies rubric linkage (`_apply_rubric_links`).
7. All question creation is wrapped in an atomic transaction.
8. Returns assessment DTO with all questions.

**Errors:**
- `ASMT-UC-01-E1`: Missing or invalid payload (title, questions).
- `ASMT-UC-01-E2`: Caller is not RESEARCHER or ADMIN.
- `ASMT-UC-01-E3`: Invalid question type not in supported enum.
- `ASMT-UC-01-E4`: Invalid grading mode not in supported enum.

**Tests (representative):**
- `test_ASMT_UC_01_RESEARCHER`
- `test_ASMT_UC_01_ADMIN`
- `test_ASMT_UC_01_E2_STUDENT`
- `test_ASMT_UC_01_E2_TEACHER`

---

### ASMT-UC-02 — List Assessments

**Roles:** ADMIN, RESEARCHER, TEACHER
**Endpoint:** `GET /api/v1/assessments`

**Main Flow:**
1. Caller requests assessment list.
2. System validates caller has TEACHER or above role.
3. System returns all assessment templates (assessments are global templates; no ownership filter).
4. Returns paginated assessment DTO list.

**Errors:**
- `ASMT-UC-02-E1`: Unauthorized role (below TEACHER).

**Tests (representative):**
- `test_ASMT_UC_02_ADMIN`
- `test_ASMT_UC_02_RESEARCHER`
- `test_ASMT_UC_02_TEACHER`
- `test_ASMT_CN_02_student_cannot_list`

---

### ASMT-UC-03 — Get Assessment Detail

**Roles:** ADMIN, RESEARCHER, TEACHER
**Endpoint:** `GET /api/v1/assessments/{assessment_id}`

**Main Flow:**
1. System resolves assessment by ID.
2. System validates caller has TEACHER or above role.
3. Returns assessment DTO with all questions and rubric linkage.

**Errors:**
- `ASMT-UC-03-E1`: Assessment not found.
- `ASMT-UC-03-E2`: Unauthorized role (below TEACHER).

**Tests (representative):**
- `test_ASMT_UC_03_ADMIN`
- `test_ASMT_UC_03_RESEARCHER`
- `test_ASMT_UC_03_TEACHER`
- `test_ASMT_CN_02_student_cannot_view`

---

### ASMT-UC-04 — Update Assessment

**Roles:** RESEARCHER, ADMIN
**Endpoint:** `PATCH /api/v1/assessments/{assessment_id}`

**Main Flow:**
1. System resolves assessment by ID.
2. System validates caller has RESEARCHER or ADMIN role.
3. System checks whether any assignments reference this assessment.
4. If assignments reference this assessment, request is rejected with `409 Conflict`.
5. System validates patch payload (`title`, `category`, `gradingMode`, `questions`).
6. System replaces all questions (full replacement, not merge; question IDs are regenerated).
7. If rubric linkage fields are updated, system applies rubric linkage.
8. All operations are wrapped in an atomic transaction.
9. Returns updated assessment DTO.

**Errors:**
- `ASMT-UC-04-E1`: Assessment not found.
- `ASMT-UC-04-E2`: Caller is not RESEARCHER or ADMIN.
- `ASMT-UC-04-E3`: Update blocked because assignments reference this assessment.
- `ASMT-UC-04-E4`: Invalid payload.

**Tests (representative):**
- `test_ASMT_UC_04_RESEARCHER`
- `test_ASMT_UC_04_E2_TEACHER`

---

### ASMT-UC-05 — Delete Assessment

**Roles:** RESEARCHER, ADMIN
**Endpoint:** `DELETE /api/v1/assessments/{assessment_id}`

**Main Flow:**
1. System resolves assessment by ID.
2. System validates caller has RESEARCHER or ADMIN role.
3. System checks whether any assignments reference this assessment.
4. If assignments reference this assessment, request is rejected with `409 Conflict`.
5. System hard-deletes assessment and all associated questions.
6. Returns `204 No Content`.

**Errors:**
- `ASMT-UC-05-E1`: Assessment not found.
- `ASMT-UC-05-E2`: Caller is not RESEARCHER or ADMIN.
- `ASMT-UC-05-E3`: Deletion blocked because assignments reference this assessment.

**Tests (representative):**
- `test_ASMT_UC_05_RESEARCHER`
- `test_ASMT_UC_05_E2_TEACHER`
- `test_ASMT_CN_05_unreferenced_delete_succeeds`

---

### ASMT-UC-06 — Archive Assessment

**Roles:** RESEARCHER, ADMIN
**Endpoint:** `POST /api/v1/assessments/{assessment_id}/archive`

**Main Flow:**
1. System resolves assessment by ID.
2. System validates caller has RESEARCHER or ADMIN role.
3. System sets assessment status to `ARCHIVED`.
4. Archived assessment remains readable by ADMIN, RESEARCHER, and TEACHER.
5. Existing assignments referencing this assessment continue to function.
6. No new assignments can be created from an archived assessment (enforced by FR-07).
7. Returns updated assessment DTO with `status: ARCHIVED`.

**Policy Requirements:**
- Archive is the recommended action when deletion is blocked by `ASMT-CN-05`.
- Once archived, an assessment can be hard-deleted only after all referencing assignments are removed.

**Errors:**
- `ASMT-UC-06-E1`: Assessment not found.
- `ASMT-UC-06-E2`: Caller is not RESEARCHER or ADMIN.
- `ASMT-UC-06-E3`: Assessment is already archived.

**Tests (representative):** _(no backend unit tests for archive — not yet implemented)_

---

## 5) Constraints

### ASMT-CN-01 — Assessment Authorship Boundary
- Only RESEARCHER and ADMIN can create, update, or delete assessment templates.
- TEACHER has read-only access. STUDENT has no ASMT domain access.
- Applies to: all ASMT UCs.

### ASMT-CN-02 — No Student Assessment Access
- Students cannot access any assessment endpoint. Students interact with assessment content only through assignments (FR-07) and submissions (FR-08).
- Current implementation uses `IsAuthenticated` on the detail endpoint; must be changed to `IsTeacherOrAbove`.
- Applies to: ASMT-UC-02, ASMT-UC-03.

### ASMT-CN-03 — Question Type Enumeration
- Supported question types: `MULTIPLE_CHOICE`, `SHORT_ANSWER`, `NUMBER_SCALE`, `MOOD_METER`.
- Future extensions (`TRUE_FALSE`, `REFLECTION`) are not part of current contract. `TRUE_FALSE` would be a 2-option MCQ variant; `REFLECTION` would be a flagged `SHORT_ANSWER` with `graded=false`.
- Applies to: ASMT-UC-01, ASMT-UC-04.

### ASMT-CN-04 — Grading Mode Enumeration
- Supported grading modes: `AUTO`, `MANUAL`, `HYBRID`, `MOOD_METER`; `RUBRIC` is accepted as an input compatibility alias and normalized to `MANUAL`.
- Grading mode determines auto-grading eligibility and rubric linkage requirements.
- Applies to: ASMT-UC-01, ASMT-UC-04.

### ASMT-CN-05 — Deletion Blocked When Referenced
- Assessment deletion returns `409 Conflict` when any assignments reference the assessment.
- Hard delete is permitted only when no assignments exist for the assessment.
- Applies to: ASMT-UC-05.

### ASMT-CN-06 — Update Blocked When Referenced
- Assessment updates return `409 Conflict` when any assignments reference the assessment.
- Prevents invalidation of existing submissions tied to the assessment's question structure.
- Applies to: ASMT-UC-04.

### ASMT-CN-07 — Rubric Linkage Within Assessment Domain
- Assessments can link to a rubric assessment via `rubric` FK (ForeignKey to self).
- When `gradingMode=RUBRIC`, the linked assessment serves as grading criteria.
- `rubric_assessment_ids` ArrayField supports multi-rubric scenarios.
- `_apply_rubric_links()` auto-updates the `rubric_id` field on target assessments when a rubric-mode assessment is created or updated.
- Applies to: ASMT-UC-01, ASMT-UC-04.

### ASMT-CN-08 — Question Replacement Semantics
- Assessment updates replace all questions (full replacement, not merge).
- Old questions are deleted; new questions are created with new IDs.
- This is why ASMT-CN-06 blocks updates when assignments reference the assessment.
- Applies to: ASMT-UC-04.

### ASMT-CN-09 — Mood Meter Auto-Configuration
- Assessments with `gradingMode=MOOD_METER` are auto-configured with a single question: prompt `"How are you feeling today?"`, `maxPoints=0`, `graded=false`.
- Caller-supplied questions are ignored for this grading mode.
- Applies to: ASMT-UC-01.

### ASMT-CN-10 — Atomic Question Provisioning
- Assessment creation and question provisioning are wrapped in a database transaction.
- Assessment update and question replacement are wrapped in a database transaction.
- Applies to: ASMT-UC-01, ASMT-UC-04.

### ASMT-CN-11 — Auto-Grading Detection
- `autoGradable` flag is determined by question type at creation time:
  - `MULTIPLE_CHOICE`: `true` (has correct answer indices).
  - `NUMBER_SCALE`: `true` (has target value).
  - `SHORT_ANSWER`: `false` (requires manual review).
  - `MOOD_METER`: `false` (no grading).
- Applies to: ASMT-UC-01, ASMT-UC-04.

### ASMT-CN-12 — Teacher Self-Assess Deprecated
- `POST /api/v1/assessments/{assessment_id}/teacher-self-assess` is deprecated.
- Route still exists in codebase; removal target: next FR-06 implementation release.
- Migration note: any dependent frontend paths must be redirected before route removal.

### ASMT-CN-13 — Assessment Archive Lifecycle
- Assessments gain a `status` field with values `ACTIVE` (default) and `ARCHIVED`.
- Archived assessments remain readable and their existing assignments continue to function.
- No new assignments can be created from an archived assessment (enforced by FR-07 ASGN at assignment creation time).
- Archived assessments can be hard-deleted via ASMT-UC-05 once all referencing assignments are removed.
- Archive is the recommended resolution when ASMT-CN-05 blocks deletion.
- Applies to: ASMT-UC-05, ASMT-UC-06.

---

## 6) Infrastructure Contract

### 6.1 Endpoint Contract

| Method | Path | Auth | UC |
|--------|------|------|-----|
| GET | `/api/v1/assessments` | IsTeacherOrAbove | ASMT-UC-02 |
| POST | `/api/v1/assessments` | IsTeacherOrAbove + researcher/admin gate | ASMT-UC-01 |
| GET | `/api/v1/assessments/{assessment_id}` | IsTeacherOrAbove | ASMT-UC-03 |
| PATCH | `/api/v1/assessments/{assessment_id}` | IsTeacherOrAbove + researcher/admin gate | ASMT-UC-04 |
| DELETE | `/api/v1/assessments/{assessment_id}` | IsTeacherOrAbove + researcher/admin gate | ASMT-UC-05 |
| POST | `/api/v1/assessments/{assessment_id}/archive` | IsTeacherOrAbove + researcher/admin gate | ASMT-UC-06 |

> **Trailing-slash note:** Django framework may accept trailing-slash variants (e.g., `/api/v1/assessments/`). Canonical paths in this contract omit the trailing slash.

**Deprecations (not part of target FR-06 contract):**
- `POST /api/v1/assessments/{assessment_id}/teacher-self-assess`
- Deprecation policy: deprecated now; remove after migration in the next FR-06 implementation release.

---

## 7) Error Model

Standard error payload:
- `{"detail": "<message>"}` for validation, not-found, or authorization errors.

Expected statuses by UC:
- `400`: invalid payload/question type/grading mode
- `403`: forbidden by role
- `404`: assessment not found
- `409`: mutation blocked by assignment references (`ASMT-UC-04-E3`, `ASMT-UC-05-E3`) or already archived (`ASMT-UC-06-E3`)
- `201`: create success
- `200`: read/update success
- `204`: delete success

---

## 8) Test Strategy by Layer

### Backend Unit
- Question type creation and validation for all 4 types.
- Grading mode validation and auto-configuration (mood meter).
- Auto-grading detection per question type.
- DTO conversion for all question types and rubric linkage.
- Rubric linkage application logic.

### Backend Integration
- Route + auth + serializer + persistence:
  - `tests/integration/test_assessments_routes.py`
  - additional FR-06 traceability tests for ASMT-CN-02/05/06/07/08/13

### Frontend Unit/Integration
- Deferred for FR-06 UI implementation phase; backend contract is source of truth for now.

### System Tests (Black Box)
- `ST-ASMT-UC-01` through `ST-ASMT-UC-06`
- Required constraint checks:
  - `ST-ASMT-CN-02` (no student assessment access)
  - `ST-ASMT-CN-05` (delete blocked when referenced)
  - `ST-ASMT-CN-06` (update blocked when referenced)
  - `ST-ASMT-CN-10` (atomic question provisioning)
  - `ST-ASMT-CN-13` (archived assessment blocks new assignments)

---

## 9) NFR Cross-References

- **NFR-Security**
  - Role gates enforced server-side (`IsTeacherOrAbove` with researcher/admin mutation gate).
  - No student access to assessment domain.
- **NFR-Reliability**
  - Question provisioning and replacement are transactional.
  - Deterministic status codes and error payloads.
  - Mutation blocked when downstream data integrity would be compromised.
- **NFR-Performance**
  - Paginated assessment listing.
  - Query paths avoid unbounded response payloads.
- **NFR-Maintainability**
  - Assessment domain behavior centralized in service layer (`assessments/services.py`).
  - Question type extensions use consistent OneToOne pattern.
  - Auto-grading detection derived from question type, not manually configured.

---

## 10) Cross-Domain References

| Domain | ASMT dependency | Integration note |
|--------|-----------------|------------------|
| FR-05 CRS | Course context for assignment creation | Assessments are global templates; course scoping happens at assignment level (FR-07) |
| FR-07 ASGN | Assignment references block mutation | ASGN-CN-04 enforces archived assessment check; ASMT-CN-05/06 block delete/update when assignments exist |
| FR-08 SUB | Submission answers tied to question structure | Question replacement (ASMT-CN-08) is blocked when submissions exist via assignment reference check |
| FR-14 ARCH | Assessment archive lifecycle | ARCH-UC-01 archives assessments; blocks new assignment creation from archived templates |

---

## 11) Current Implementation Alignment Notes

This draft defines the target FR-06 contract. Current code has known deltas that must be resolved before FR-06 can be marked COMPLETE:

1. Change assessment detail endpoint auth from `IsAuthenticated` to `IsTeacherOrAbove` (ASMT-CN-02).
2. Add `409 Conflict` response for delete when assignments reference assessment (ASMT-CN-05).
3. Add `409 Conflict` response for update when assignments reference assessment (ASMT-CN-06).
4. Remove deprecated `teacher-self-assess` route from `urls.py` and its view handler (ASMT-CN-12).
5. Add assignment reference check in delete and update service paths.
6. Stop delete service from cascading through assignments; current `delete_assessment` hard-deletes downstream assignments first, which violates ASMT-CN-05.
7. Add `status` field (`ACTIVE`/`ARCHIVED`) to Assessment model and archive endpoint (ASMT-CN-13). Implementation deferred; archive lifecycle will be addressed in a future release.
8. Add missing FR-06 traceability tests for constraints and error paths.
9. Preserve paginated listing behavior on `GET /api/v1/assessments` during FR-06 changes.

---

## 12) Rubric Entity Extension (FR-06 Addendum, Draft v1)

This addendum updates FR-06 direction to support a full rubric system where rubrics are first-class grading tools, not assessment templates.

### 12.1 Decision and Scope

- Rubric is a standalone domain entity.
- Assessments remain content templates; rubrics define manual grading criteria.
- Rubrics can be attached per question or per question group.
- `trimWhitespace` and `caseSensitive` remain short-answer config flags and must be explained in the builder UI.

When this addendum is implemented, it supersedes current self-referential rubric linkage behavior described in `ASMT-CN-07`.

### 12.2 Updated Grading Semantics

- `AUTO`: all gradable questions are auto-graded; manual rubric attachment is disallowed.
- `MANUAL`: all gradable questions require rubric linkage (direct or inherited via group).
- `HYBRID`: mixture of auto-graded and rubric-graded questions is allowed.
- `RUBRIC`: compatibility alias for `MANUAL` during migration; new UI should not surface this as a separate authoring mode.
- `MOOD_METER`: no scoring; no rubric linkage.

### 12.3 Backend Data Model (Target)

Add standalone rubric models:

- `Rubric`
  - `id`
  - `title` (required)
  - `description` (optional)
  - `status` (`ACTIVE` or `ARCHIVED`)
  - `created_by` (ADMIN/RESEARCHER)
  - `created_at`, `updated_at`
- `RubricCriterion`
  - `id`
  - `rubric_id` (FK)
  - `title` (required)
  - `description` (optional)
  - `order_index`
  - `weight` (default `1.0`)
- `RubricLevel`
  - `id`
  - `criterion_id` (FK)
  - `label` (required, example: `Excellent`, `Proficient`, `Developing`)
  - `points` (numeric)
  - `description` (optional)
  - `order_index`

Add question grouping for shared rubric assignment:

- `AssessmentQuestionGroup`
  - `id`
  - `assessment_id` (FK)
  - `name` (required)
  - `rubric_id` (nullable FK)
  - `order_index`
- `Question`
  - add `question_group_id` (nullable FK)
  - add `rubric_id` (nullable FK override)
  - keep existing type-specific extension models

Resolution order for rubric at grading time:
1. `question.rubric_id` (question override)
2. `question.question_group.rubric_id` (group default)
3. none (invalid for `MANUAL`, allowed only in `AUTO` and manual-optional modes)

### 12.4 API Contract (Rubrics)

New rubric endpoints:

| Method | Path | Auth | Behavior |
|--------|------|------|----------|
| GET | `/api/v1/rubrics` | IsTeacherOrAbove | List rubrics (teachers read-only) |
| POST | `/api/v1/rubrics` | IsTeacherOrAbove + researcher/admin gate | Create rubric |
| GET | `/api/v1/rubrics/{rubric_id}` | IsTeacherOrAbove | Rubric detail |
| PATCH | `/api/v1/rubrics/{rubric_id}` | IsTeacherOrAbove + researcher/admin gate | Update rubric (blocked if policy requires immutability after use) |
| DELETE | `/api/v1/rubrics/{rubric_id}` | IsTeacherOrAbove + researcher/admin gate | Delete rubric if unreferenced; else `409` |
| POST | `/api/v1/rubrics/{rubric_id}/archive` | IsTeacherOrAbove + researcher/admin gate | Archive rubric (`ACTIVE` -> `ARCHIVED`) |

Assessment payload updates:

- Remove `rubricId` and `rubricAssessmentIds` from assessment-level payload.
- Add optional `questionGroups` and per-question rubric linkage:
  - `questionGroups[]`: `{ clientKey, name, rubricId? }`
  - `questions[]`: include `groupClientKey?` and `rubricId?`

Compatibility note:
- Existing clients posting `rubricId`/`rubricAssessmentIds` should receive `400` with migration guidance after rollout completion.

### 12.5 Validation Rules

- `MANUAL`: every gradable question must resolve to a rubric via question or group.
- `HYBRID`: questions marked manual must resolve to rubric; auto-graded questions must not carry rubric.
- `AUTO`: rubric linkage is invalid and returns `400`.
- `MOOD_METER`: no rubric linkage; questions are auto-configured as today.
- Rubric delete/update:
  - `409` when rubric is referenced by assessments, groups, or persisted grading artifacts.
- Assessment update/delete:
  - keep existing `409` assignment-reference protections.

### 12.6 Frontend Builder Contract

#### Page placement

- Keep assessment authoring under:
  - `/dashboard/assessments`
  - `/dashboard/assessments/new`
  - `/dashboard/assessments/[id]`
  - `/dashboard/assessments/[id]/edit`
- Add rubric authoring under:
  - `/dashboard/rubrics`
  - `/dashboard/rubrics/new`
  - `/dashboard/rubrics/[id]`
  - `/dashboard/rubrics/[id]/edit`

#### Assessment builder UX requirements

- Metadata block:
  - `title`, `category`, `gradingMode`
- Question builder:
  - add/remove/reorder questions
  - per-question type-specific fields
  - per-question grading selector (`Auto` or `Manual`) when mode is `HYBRID`
  - per-question rubric selector (optional override)
- Question groups:
  - create named groups
  - assign group-level rubric
  - assign questions to group

#### Required helper text (short answer)

- `Trim Whitespace`: "Ignores extra spaces at the start/end and treats repeated spaces as equivalent when comparing answers."
- `Case Sensitive`: "When enabled, uppercase/lowercase must match exactly (example: `DNA` is different from `dna`)."

#### Rubric authoring UX requirements

- Criterion rows with reorder support.
- Level columns with explicit points per level.
- Live total-points preview per criterion and per rubric.
- Guardrail: prevent save when any criterion has zero levels.

### 12.7 Migration Plan

Phase A (compatibility):
- Add new rubric tables and endpoints.
- Keep legacy assessment rubric fields read-only in DTO output for one release.
- Add server-side mapping from legacy linkage to new question/group linkage when feasible.

Phase B (cutover):
- Update frontend to use standalone rubric APIs.
- Stop sending legacy `rubricId` and `rubricAssessmentIds`.
- Add data migration to populate `Question.rubric_id` and/or `AssessmentQuestionGroup.rubric_id`.

Phase C (cleanup):
- Remove legacy assessment rubric fields and linkage helper code (`_apply_rubric_links` path).
- Remove compatibility alias `RUBRIC` from authoring UI (backend may keep enum alias for backward compatibility).

### 12.8 Testing Additions

Backend integration additions:
- `ASMT-RBX-UC-01`: create rubric with criteria+levels.
- `ASMT-RBX-UC-02`: attach rubric to manual questions/groups in assessment create.
- `ASMT-RBX-UC-03`: reject `MANUAL` assessment with unresolved rubric linkage (`400`).
- `ASMT-RBX-UC-04`: reject rubric deletion when referenced (`409`).
- `ASMT-RBX-UC-05`: teacher can list/view rubrics but cannot mutate (`403` on write).

Frontend tests:
- Question builder shows helper text for `Trim Whitespace` and `Case Sensitive`.
- `HYBRID` mode supports mixed auto/manual question configuration.
- Manual question cannot submit without rubric.

### 12.9 Recommended Implementation Order

1. Ship rubric backend models + CRUD + permissions.
2. Add question/group rubric linkage in assessment APIs.
3. Enforce validation rules for `MANUAL` and `HYBRID`.
4. Build rubric UI pages.
5. Integrate rubric selectors into assessment builder.
6. Remove legacy rubric-as-assessment linkage.
