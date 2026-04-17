# FR-06 Assignment Templates (ATMPL) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | ATMPL |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER |
| **Related Issues** | TBD |
| **Dependencies** | FR-07 ASGN (assignment usage), FR-08 SUB (submission data), FR-14 ARCH (archive lifecycle) |

---

## 1) Scope

### In Scope
- AssignmentTemplate template lifecycle for researcher-authored templates:
  - create assignment template with questions
  - list available assignment templates
  - read assignment template detail
  - update assignment template (only before it has ever been used)
  - delete assignment template (for drafts or active templates that have never been used)
- 4 question types (current backend): `MULTIPLE_CHOICE`, `SHORT_ANSWER`, `NUMBER_SCALE`, `MOOD_METER`.
- Grading modes in active backend contract: `AUTO`, `MANUAL`, `HYBRID`, `MOOD_METER`, with `RUBRIC` accepted as an input compatibility alias that persists as `MANUAL`.
- Rubric linkage/lifecycle within assignment template domain (assignment template-linked `rubric` FK + `rubric_assignment_template_ids`).
- Authorization matrix:
  - RESEARCHER/ADMIN: full CRUD
  - TEACHER: read-only visibility for ACTIVE published templates
  - STUDENT: no ATMPL domain access
- Usage-aware mutation policy: never-used ACTIVE templates allow update/delete; historically used templates are archive-first and return `409 Conflict` for update/delete.
- Draft lifecycle: drafts can be published or deleted, but not archived.
- AssignmentTemplate archive lifecycle: historically used templates can be archived to prevent new assignment creation while preserving existing assignments.
- Auto-grading detection per question type.
- Atomic question provisioning within assignment template create/update.

### Out of Scope
- Student assignment template access (students interact through assignments/submissions in FR-07/FR-08 only).
- Assignment creation from assignment templates (FR-07 ASGN).
- Submission, answer, and grading flows (FR-08 SUB).
- AssignmentTemplate subset selection for assignments (FR-07 decision).
- Rubric as a standalone entity (current model uses assignment template-linked fields; standalone rubric entity is a future architectural decision).
- Future question types: `TRUE_FALSE`, `REFLECTION` (planned extensions; not in current backend contract).
- UI wireframes and future browser smoke flows (tracked separately).

### Deprecations
- No deprecated assignment template routes remain in the active FR-06 contract.

### Core Intent
- Provide researcher-authored assignment templates with multi-type question support and grading mode configuration.
- Enforce a usage-aware mutation policy: never-used templates allow normal mutation; historically used templates are protected by archive-first lifecycle rules.
- Support assignment template archive lifecycle to retire templates without breaking existing assignments.

---

## 2) Actors

| Role | Type | ATMPL domain permissions |
|------|------|--------------------------|
| ADMIN | System role (`is_staff=True`) | Full CRUD on assignment templates; same permissions as RESEARCHER |
| RESEARCHER | User role | Full CRUD on assignment templates; primary assignment template author |
| TEACHER | User role | Read-only visibility across all assignment templates |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER

> **Note:** STUDENT has no ATMPL domain access. Students see assignment template content only through assignments (FR-07) and submissions (FR-08).

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| ATMPL-US-01 | RESEARCHER, ADMIN | As a researcher or admin I can create an assignment template with questions so that teachers can assign it to their courses. |
| ATMPL-US-02 | ADMIN, RESEARCHER, TEACHER | As an admin, researcher, or teacher I can view available assignment templates so that I can review content or select templates for assignment. |
| ATMPL-US-03 | RESEARCHER, ADMIN | As a researcher or admin I can update an assignment template before it has been used so that I can correct or improve questions before distribution. |
| ATMPL-US-04 | RESEARCHER, ADMIN | As a researcher or admin I can delete an unused assignment template so that the template library stays clean without preserving unused drafts or active templates. |
| ATMPL-US-05 | RESEARCHER, ADMIN | As a researcher or admin I can link a rubric to an assignment template so that grading criteria are attached to the template. |
| ATMPL-US-06 | RESEARCHER, ADMIN | As a researcher or admin I can archive a historically used assignment template so that no new assignments are created from it while existing assignments remain valid. |

---

## 4) Use Cases

### ATMPL-UC-01 — Create AssignmentTemplate

**Roles:** RESEARCHER, ADMIN
**Endpoint:** `POST /api/v1/assignment-templates`

**Main Flow:**
1. Caller submits assignment template payload: `title`, optional `category`, `gradingMode`, `questions` array, optional `rubricId`, optional `rubricAssignmentTemplateIds`.
2. System validates caller has RESEARCHER or ADMIN role.
3. System validates `gradingMode` against supported enum.
4. If `gradingMode` is `MOOD_METER`, system delegates to mood meter auto-configuration (single pre-set question, `maxPoints=0`, `graded=false`).
5. For each question in the `questions` array:
   - System validates `type` against supported question kind enum.
   - System creates base `Question` record and type-specific extension model.
   - System determines `autoGradable` flag: `true` for `MULTIPLE_CHOICE` and `NUMBER_SCALE`; `false` for `SHORT_ANSWER` and `MOOD_METER`.
6. If `rubricId` is provided, system applies rubric linkage (`_apply_rubric_links`).
7. All question creation is wrapped in an atomic transaction.
8. Returns assignment template DTO with all questions.

**Errors:**
- `ATMPL-UC-01-E1`: Missing or invalid payload (title, questions).
- `ATMPL-UC-01-E2`: Caller is not RESEARCHER or ADMIN.
- `ATMPL-UC-01-E3`: Invalid question type not in supported enum.
- `ATMPL-UC-01-E4`: Invalid grading mode not in supported enum.

**Tests (representative):**
- `test_ATMPL_UC_01_RESEARCHER`
- `test_ATMPL_UC_01_ADMIN`
- `test_ATMPL_UC_01_E2_STUDENT`
- `test_ATMPL_UC_01_E2_TEACHER`

---

### ATMPL-UC-02 — List AssignmentTemplates

**Roles:** ADMIN, RESEARCHER, TEACHER
**Endpoint:** `GET /api/v1/assignment-templates`

**Main Flow:**
1. Caller requests assignment template list.
2. System validates caller has TEACHER or above role.
3. System returns all assignment templates (assignment templates are global templates; no ownership filter).
4. Returns paginated assignment template DTO list.

**Errors:**
- `ATMPL-UC-02-E1`: Unauthorized role (below TEACHER).

**Tests (representative):**
- `test_ATMPL_UC_02_ADMIN`
- `test_ATMPL_UC_02_RESEARCHER`
- `test_ATMPL_UC_02_TEACHER`
- `test_ATMPL_CN_02_student_cannot_list`

---

### ATMPL-UC-03 — Get AssignmentTemplate Detail

**Roles:** ADMIN, RESEARCHER, TEACHER
**Endpoint:** `GET /api/v1/assignment-templates/{assignment_template_id}`

**Main Flow:**
1. System resolves assignment template by ID.
2. System validates caller has TEACHER or above role.
3. Teachers can read only `ACTIVE` published templates; draft and archived templates remain researcher/admin-only detail views.
4. Returns assignment template DTO with all questions and rubric linkage.

**Errors:**
- `ATMPL-UC-03-E1`: AssignmentTemplate not found.
- `ATMPL-UC-03-E2`: Unauthorized role (below TEACHER) or teacher tries to access non-active template detail.

**Tests (representative):**
- `test_ATMPL_UC_03_ADMIN`
- `test_ATMPL_UC_03_RESEARCHER`
- `test_ATMPL_UC_03_TEACHER`
- `test_ATMPL_CN_02_student_cannot_view`

---

### ATMPL-UC-04 — Update AssignmentTemplate

**Roles:** RESEARCHER, ADMIN
**Endpoint:** `PATCH /api/v1/assignment-templates/{assignment_template_id}`

**Main Flow:**
1. System resolves assignment template by ID.
2. System validates caller has RESEARCHER or ADMIN role.
3. System checks whether the assignment template has ever been used by an assignment.
4. If the template has ever been used, request is rejected with `409 Conflict`.
5. System validates patch payload (`title`, `category`, `gradingMode`, `questions`).
6. System replaces all questions (full replacement, not merge; question IDs are regenerated).
7. If rubric linkage fields are updated, system applies rubric linkage.
8. All operations are wrapped in an atomic transaction.
9. Returns updated assignment template DTO.

**Errors:**
- `ATMPL-UC-04-E1`: AssignmentTemplate not found.
- `ATMPL-UC-04-E2`: Caller is not RESEARCHER or ADMIN.
- `ATMPL-UC-04-E3`: Update blocked because the assignment template has already been used by assignments.
- `ATMPL-UC-04-E4`: Invalid payload.

**Tests (representative):**
- `test_ATMPL_UC_04_RESEARCHER`
- `test_ATMPL_UC_04_E2_TEACHER`

---

### ATMPL-UC-05 — Delete AssignmentTemplate

**Roles:** RESEARCHER, ADMIN
**Endpoint:** `DELETE /api/v1/assignment-templates/{assignment_template_id}`

**Main Flow:**
1. System resolves assignment template by ID.
2. System validates caller has RESEARCHER or ADMIN role.
3. If the assignment template is a draft, system hard-deletes it directly.
4. If the assignment template is ACTIVE and has never been used, system hard-deletes it and all associated questions.
5. If the assignment template has ever been used, request is rejected with `409 Conflict` and caller must archive it instead.
6. If the assignment template is ARCHIVED, plain delete is rejected with `409 Conflict` and caller must use `?purge=true`.
7. Returns `204 No Content` on successful draft or unused-template delete.

**Errors:**
- `ATMPL-UC-05-E1`: AssignmentTemplate not found.
- `ATMPL-UC-05-E2`: Caller is not RESEARCHER or ADMIN.
- `ATMPL-UC-05-E3`: Deletion blocked because the assignment template has already been used by assignments.

**Tests (representative):**
- `test_ATMPL_UC_05_RESEARCHER`
- `test_ATMPL_UC_05_E2_TEACHER`
- `test_ATMPL_CN_05_used_delete_requires_archive`

---

### ATMPL-UC-06 — Archive AssignmentTemplate

**Roles:** RESEARCHER, ADMIN
**Endpoint:** `POST /api/v1/assignment-templates/{assignment_template_id}/archive`

**Main Flow:**
1. System resolves assignment template by ID.
2. System validates caller has RESEARCHER or ADMIN role.
3. System sets assignment template status to `ARCHIVED`.
4. Archived assignment template remains readable by ADMIN, RESEARCHER, and TEACHER.
5. Existing assignments referencing this assignment template continue to function.
6. No new assignments can be created from an archived assignment template (enforced by FR-07).
7. Returns updated assignment template DTO with `status: ARCHIVED`.

**Policy Requirements:**
- Archive is the recommended action when deletion is blocked by `ATMPL-CN-05`.
- Once archived, an assignment template can be hard-deleted only when it satisfies the archive/purge lifecycle rules for historically used templates.

**Errors:**
- `ATMPL-UC-06-E1`: AssignmentTemplate not found.
- `ATMPL-UC-06-E2`: Caller is not RESEARCHER or ADMIN.
- `ATMPL-UC-06-E3`: AssignmentTemplate is already archived.

**Tests (representative):** _(no backend unit tests for archive — not yet implemented)_

---

## 5) Constraints

### ATMPL-CN-01 — AssignmentTemplate Authorship Boundary
- Only RESEARCHER and ADMIN can create, update, or delete assignment templates.
- TEACHER has read-only access. STUDENT has no ATMPL domain access.
- Applies to: all ATMPL UCs.

### ATMPL-CN-02 — No Student AssignmentTemplate Access
- Students cannot access any assignment template endpoint. Students interact with assignment template content only through assignments (FR-07) and submissions (FR-08).
- Current implementation uses `IsAuthenticated` on the detail endpoint; must be changed to `IsTeacherOrAbove`.
- Applies to: ATMPL-UC-02, ATMPL-UC-03.

### ATMPL-CN-03 — Question Type Enumeration
- Supported question types: `MULTIPLE_CHOICE`, `SHORT_ANSWER`, `NUMBER_SCALE`, `MOOD_METER`.
- Future extensions (`TRUE_FALSE`, `REFLECTION`) are not part of current contract. `TRUE_FALSE` would be a 2-option MCQ variant; `REFLECTION` would be a flagged `SHORT_ANSWER` with `graded=false`.
- Applies to: ATMPL-UC-01, ATMPL-UC-04.

### ATMPL-CN-04 — Grading Mode Enumeration
- Supported grading modes: `AUTO`, `MANUAL`, `HYBRID`, `MOOD_METER`; `RUBRIC` is accepted as an input compatibility alias and normalized to `MANUAL`.
- Grading mode determines auto-grading eligibility and rubric linkage requirements.
- Applies to: ATMPL-UC-01, ATMPL-UC-04.

### ATMPL-CN-05 — Historically Used Templates Are Archive-First
- AssignmentTemplate deletion returns `409 Conflict` when the assignment template has ever been used by an assignment.
- Hard delete is permitted only for drafts and active templates that have never been used.
- Applies to: ATMPL-UC-05.

### ATMPL-CN-06 — Update Blocked After Use
- AssignmentTemplate updates return `409 Conflict` when the assignment template has ever been used by an assignment.
- Prevents invalidation of downstream assignment and submission context tied to the assignment template's question structure.
- Applies to: ATMPL-UC-04.

### ATMPL-CN-07 — Rubric Linkage Within AssignmentTemplate Domain
- AssignmentTemplates can link to a rubric assignment template via `rubric` FK (ForeignKey to self).
- When `gradingMode=RUBRIC`, the linked assignment template serves as grading criteria.
- `rubric_assignment_template_ids` ArrayField supports multi-rubric scenarios.
- `_apply_rubric_links()` auto-updates the `rubric_id` field on target assignment templates when a rubric-mode assignment template is created or updated.
- Applies to: ATMPL-UC-01, ATMPL-UC-04.

### ATMPL-CN-08 — Question Replacement Semantics
- AssignmentTemplate updates replace all questions (full replacement, not merge).
- Old questions are deleted; new questions are created with new IDs.
- This is why ATMPL-CN-06 blocks updates once the assignment template has been used.
- Applies to: ATMPL-UC-04.

### ATMPL-CN-09 — Mood Meter Auto-Configuration
- AssignmentTemplates with `gradingMode=MOOD_METER` are auto-configured with a single question: prompt `"How are you feeling today?"`, `maxPoints=0`, `graded=false`.
- Caller-supplied questions are ignored for this grading mode.
- Applies to: ATMPL-UC-01.

### ATMPL-CN-10 — Atomic Question Provisioning
- AssignmentTemplate creation and question provisioning are wrapped in a database transaction.
- AssignmentTemplate update and question replacement are wrapped in a database transaction.
- Applies to: ATMPL-UC-01, ATMPL-UC-04.

### ATMPL-CN-11 — Auto-Grading Detection
- `autoGradable` flag is determined by question type at creation time:
  - `MULTIPLE_CHOICE`: `true` (has correct answer indices).
  - `NUMBER_SCALE`: `true` (has target value).
  - `SHORT_ANSWER`: `false` (requires manual review).
  - `MOOD_METER`: `false` (no grading).
- Applies to: ATMPL-UC-01, ATMPL-UC-04.

### ATMPL-CN-12 — No Teacher Self-Assess Compatibility Route
- No legacy teacher self-assignment compatibility route is part of the active FR-06 contract.
- No compatibility route is retained after the hard cutover.

### ATMPL-CN-13 — AssignmentTemplate Archive Lifecycle
- AssignmentTemplates gain a `status` field with values `ACTIVE` (default) and `ARCHIVED`.
- Archived assignment templates remain readable and their existing assignments continue to function.
- No new assignments can be created from an archived assignment template (enforced by FR-07 ASGN at assignment creation time).
- Archived assignment templates can be hard-deleted via ATMPL-UC-05 only through the explicit purge path and only when lifecycle eligibility checks pass.
- Archive is the recommended resolution when ATMPL-CN-05 blocks deletion.
- Applies to: ATMPL-UC-05, ATMPL-UC-06.

---

## 6) Infrastructure Contract

### 6.1 Endpoint Contract

| Method | Path | Auth | UC |
|--------|------|------|-----|
| GET | `/api/v1/assignment-templates` | IsTeacherOrAbove | ATMPL-UC-02 |
| POST | `/api/v1/assignment-templates` | IsTeacherOrAbove + researcher/admin gate | ATMPL-UC-01 |
| GET | `/api/v1/assignment-templates/{assignment_template_id}` | IsTeacherOrAbove | ATMPL-UC-03 |
| PATCH | `/api/v1/assignment-templates/{assignment_template_id}` | IsTeacherOrAbove + researcher/admin gate | ATMPL-UC-04 |
| DELETE | `/api/v1/assignment-templates/{assignment_template_id}` | IsTeacherOrAbove + researcher/admin gate | ATMPL-UC-05 |
| POST | `/api/v1/assignment-templates/{assignment_template_id}/archive` | IsTeacherOrAbove + researcher/admin gate | ATMPL-UC-06 |

> **Trailing-slash note:** Django framework may accept trailing-slash variants (e.g., `/api/v1/assignment-templates/`). Canonical paths in this contract omit the trailing slash.

**Deprecated routes:** none.

---

## 7) Error Model

Standard error payload:
- `{"detail": "<message>"}` for validation, not-found, or authorization errors.

Expected statuses by UC:
- `400`: invalid payload/question type/grading mode
- `403`: forbidden by role
- `404`: assignment template not found
- `409`: mutation blocked by lifecycle usage rules (`ATMPL-UC-04-E3`, `ATMPL-UC-05-E3`) or already archived (`ATMPL-UC-06-E3`)
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
  - `tests/integration/test_assignment_templates_routes.py`
  - additional FR-06 traceability tests for ATMPL-CN-02/05/06/07/08/13

### Frontend Unit/Integration
- Deferred for FR-06 UI implementation phase; backend contract is source of truth for now.

### System Tests (Black Box)
- `ST-ATMPL-UC-01` through `ST-ATMPL-UC-06`
- Required constraint checks:
  - `ST-ATMPL-CN-02` (no student assignment template access)
  - `ST-ATMPL-CN-05` (delete blocked once used)
  - `ST-ATMPL-CN-06` (update blocked once used)
  - `ST-ATMPL-CN-10` (atomic question provisioning)
  - `ST-ATMPL-CN-13` (archived assignment template blocks new assignments)

---

## 9) NFR Cross-References

- **NFR-Security**
  - Role gates enforced server-side (`IsTeacherOrAbove` with researcher/admin mutation gate).
  - No student access to assignment template domain.
- **NFR-Reliability**
  - Question provisioning and replacement are transactional.
  - Deterministic status codes and error payloads.
  - Mutation blocked when downstream data integrity would be compromised.
- **NFR-Performance**
  - Paginated assignment template listing.
  - Query paths avoid unbounded response payloads.
- **NFR-Maintainability**
  - AssignmentTemplate domain behavior centralized in service layer (`assignment_templates/services.py`).
  - Question type extensions use consistent OneToOne pattern.
  - Auto-grading detection derived from question type, not manually configured.

---

## 10) Cross-Domain References

| Domain | ATMPL dependency | Integration note |
|--------|-----------------|------------------|
| FR-05 CRS | Course context for assignment creation | AssignmentTemplates are global templates; course scoping happens at assignment level (FR-07) |
| FR-07 ASGN | Assignment usage establishes lifecycle history | ASGN-CN-04 enforces archived assignment template check; ATMPL-CN-05/06 block delete/update once a template has been used |
| FR-08 SUB | Submission answers tied to question structure | Question replacement (ATMPL-CN-08) is blocked once assignment-template usage has begun, preserving downstream submission context |
| FR-14 ARCH | AssignmentTemplate archive lifecycle | ARCH-UC-01 archives assignment templates; blocks new assignment creation from archived templates |

---

## 11) Current Implementation Alignment Notes

The active implementation now matches the route-level FR-06 contract for assignment template CRUD and lifecycle enforcement:
1. Draft templates can be hard-deleted but cannot be archived.
2. Active unused templates can be hard-deleted.
3. Historically used templates are archive-first even if downstream assignments have since been removed.
4. Archived templates are readable to researcher/admin callers and purge-only on the destructive path.
5. Remaining FR-06 follow-up is limited to documentation and broader archive/export integration work, not core route semantics.

---

## 12) Rubric Entity Extension (FR-06 Addendum, Draft v1)

This addendum updates FR-06 direction to support a full rubric system where rubrics are first-class grading tools, not assignment templates.

### 12.1 Decision and Scope

- Rubric is a standalone domain entity.
- AssignmentTemplates remain content templates; rubrics define manual grading criteria.
- Rubrics can be attached per question or per question group.
- `trimWhitespace` and `caseSensitive` remain short-answer config flags and must be explained in the builder UI.

When this addendum is implemented, it supersedes current self-referential rubric linkage behavior described in `ATMPL-CN-07`.

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

- `AssignmentTemplateQuestionGroup`
  - `id`
  - `assignment_template_id` (FK)
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

AssignmentTemplate payload updates:

- Remove `rubricId` and `rubricAssignmentTemplateIds` from assignment template-level payload.
- Add optional `questionGroups` and per-question rubric linkage:
  - `questionGroups[]`: `{ clientKey, name, rubricId? }`
  - `questions[]`: include `groupClientKey?` and `rubricId?`

Compatibility note:
- Existing clients posting `rubricId`/`rubricAssignmentTemplateIds` should receive `400` with migration guidance after rollout completion.

### 12.5 Validation Rules

- `MANUAL`: every gradable question must resolve to a rubric via question or group.
- `HYBRID`: questions marked manual must resolve to rubric; auto-graded questions must not carry rubric.
- `AUTO`: rubric linkage is invalid and returns `400`.
- `MOOD_METER`: no rubric linkage; questions are auto-configured as today.
- Rubric delete/update:
  - `409` when rubric is referenced by assignment templates, groups, or persisted grading artifacts.
- AssignmentTemplate update/delete:
  - keep existing `409` assignment-reference protections.

### 12.6 Frontend Builder Contract

#### Page placement

- Keep assignment template authoring under:
  - `/dashboard/assignment-templates`
  - `/dashboard/assignment-templates/new`
  - `/dashboard/assignment-templates/[id]`
  - `/dashboard/assignment-templates/[id]/edit`
- Add rubric authoring under:
  - `/dashboard/rubrics`
  - `/dashboard/rubrics/new`
  - `/dashboard/rubrics/[id]`
  - `/dashboard/rubrics/[id]/edit`

#### AssignmentTemplate builder UX requirements

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
- Keep legacy assignment template rubric fields read-only in DTO output for one release.
- Add server-side mapping from legacy linkage to new question/group linkage when feasible.

Phase B (cutover):
- Update frontend to use standalone rubric APIs.
- Stop sending legacy `rubricId` and `rubricAssignmentTemplateIds`.
- Add data migration to populate `Question.rubric_id` and/or `AssignmentTemplateQuestionGroup.rubric_id`.

Phase C (cleanup):
- Remove legacy assignment template rubric fields and linkage helper code (`_apply_rubric_links` path).
- Remove compatibility alias `RUBRIC` from authoring UI (backend may keep enum alias for backward compatibility).

### 12.8 Testing Additions

Backend integration additions:
- `ATMPL-RBX-UC-01`: create rubric with criteria+levels.
- `ATMPL-RBX-UC-02`: attach rubric to manual questions/groups in assignment template create.
- `ATMPL-RBX-UC-03`: reject `MANUAL` assignment template with unresolved rubric linkage (`400`).
- `ATMPL-RBX-UC-04`: reject rubric deletion when referenced (`409`).
- `ATMPL-RBX-UC-05`: teacher can list/view rubrics but cannot mutate (`403` on write).

Frontend tests:
- Question builder shows helper text for `Trim Whitespace` and `Case Sensitive`.
- `HYBRID` mode supports mixed auto/manual question configuration.
- Manual question cannot submit without rubric.

### 12.9 Recommended Implementation Order

1. Ship rubric backend models + CRUD + permissions.
2. Add question/group rubric linkage in assignment template APIs.
3. Enforce validation rules for `MANUAL` and `HYBRID`.
4. Build rubric UI pages.
5. Integrate rubric selectors into assignment template builder.
6. Remove legacy rubric-as-assignment template linkage.
