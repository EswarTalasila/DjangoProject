# FR-14 Lifecycle and Archival (ARCH) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | DRAFT |
| **Date** | 2026-03-01 |
| **Domain** | ARCH |
| **Applies To** | ADMIN, RESEARCHER, TEACHER |
| **Related Issues** | TBD |
| **Dependencies** | FR-05 CRS, FR-06 ASMT, FR-07 ASGN, FR-08 SUB, FR-10 EXP, FR-11 OBS |

---

## 1) Scope

### In Scope
- Common lifecycle model for archive/restore/purge across core learning entities.
- Status transitions for:
  - Course (CRS)
  - Assessment template (ASMT)
  - Assignment (ASGN)
- Soft archive behavior (non-destructive, reversible).
- Restore behavior and ownership/role gates.
- Purge eligibility rules and conflict handling (`409`).
- Default read filtering behavior (`ACTIVE` only unless caller opts in).
- Cross-domain behavior requirements for archived data in SUB, VIZ, and EXP.
- Audit requirements for all lifecycle actions.

### Out of Scope
- Student account archival.
- Automatic legal retention policy by jurisdiction.
- Backup/restore infrastructure (FR-13 INFRA).
- Historical data anonymization job.
- UI wireframes and Playwright flows.

### Core intent
- Replace unsafe hard-delete behavior with explicit lifecycle transitions.
- Keep data recoverable during normal operations.
- Make destructive operations explicit, audited, and constrained.

---

## 2) Actors

| Role | Type | ARCH domain permissions |
|------|------|-------------------------|
| ADMIN | System role (`is_staff=True`) | Can archive/restore/purge any ARCH-managed entity when policy allows |
| RESEARCHER | User role | Read visibility for archived metadata where source FR grants read; assessment archive/restore rights follow FR-06 ASMT role gates; no default course/assignment archive or purge rights |
| TEACHER | User role | Archive/restore own courses and own assignments; cannot archive assessment templates they do not own (ASMT-owned domain) |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER

> **STUDENT excluded:** Students have no ARCH mutation operations.

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| ARCH-US-01 | TEACHER | As a teacher I can archive a course instead of deleting it so existing student work is preserved. |
| ARCH-US-02 | TEACHER | As a teacher I can archive an assignment to stop new submissions without losing existing submissions. |
| ARCH-US-03 | ADMIN, RESEARCHER | As a privileged user I can inspect archived records when troubleshooting or auditing. |
| ARCH-US-04 | ADMIN, RESEARCHER, TEACHER | As an admin, researcher, or teacher I can restore archived entities I have rights to when records were archived in error. |
| ARCH-US-05 | ADMIN | As an admin I can purge archived records only when retention and dependency rules allow it. |
| ARCH-US-06 | ADMIN | As an admin I can rely on an audit trail for all lifecycle mutations. |

---

## 4) Use Cases

### ARCH-UC-01 — Archive Assessment Template

**Roles:** ADMIN, RESEARCHER (ASMT-authorized roles)  
**Endpoint:** `POST /api/v1/assessments/{assessment_id}/archive`

**Main Flow:**
1. Caller requests archive for an assessment template.
2. System validates caller can mutate assessments (ASMT role gate).
3. System verifies assessment exists and is `ACTIVE`.
4. System sets `status=ARCHIVED`, `archivedAt`, `archivedBy`.
5. System returns updated assessment DTO.
6. New assignments using this assessment are blocked (`409`) after archive.

**Postconditions:**
- Existing assignments referencing this assessment remain valid and readable.
- Assessment no longer available for new assignment creation.

**Errors:**
- `ARCH-UC-01-E1`: Assessment not found (`404`).
- `ARCH-UC-01-E2`: Unauthorized role (`403`).
- `ARCH-UC-01-E3`: Assessment already archived (`409`).

**Tests (representative):**
- `test_ARCH_UC_01_ADMIN`
- `test_ARCH_UC_01_RESEARCHER`
- `test_ARCH_UC_01_E2`
- `test_ARCH_CN_03_assignment_create_blocked_when_assessment_archived`

---

### ARCH-UC-02 — Archive Assignment

**Roles:** TEACHER (creator/owner), ADMIN (override)  
**Endpoint:** `POST /api/v1/assignments/{assignment_id}/archive`

**Main Flow:**
1. Caller requests archive for assignment.
2. System validates ownership gate:
   - TEACHER: must own assignment.
   - ADMIN: global override.
3. System verifies assignment exists and is `ACTIVE`.
4. System sets assignment `status=ARCHIVED`, `archivedAt`, `archivedBy`.
5. System enforces assignment-archive status gate at SUB write endpoints; draft/save/submit return `409` while assignment is `ARCHIVED`.
6. System returns updated assignment DTO.

**Postconditions:**
- New draft saves and submissions are blocked.
- Existing submitted/graded records remain readable.

**Errors:**
- `ARCH-UC-02-E1`: Assignment not found (`404`).
- `ARCH-UC-02-E2`: Teacher not owner (`403`).
- `ARCH-UC-02-E3`: Assignment already archived (`409`).

**Tests (representative):**
- `test_ARCH_UC_02_TEACHER_owner`
- `test_ARCH_UC_02_ADMIN_override`
- `test_ARCH_UC_02_E2`
- `test_ARCH_CN_04_submission_writes_blocked_after_archive`

---

### ARCH-UC-03 — Archive Course

**Roles:** TEACHER (owner), ADMIN (override)  
**Endpoint:** `POST /api/v1/courses/{course_id}/archive`

**Main Flow:**
1. Caller requests course archive.
2. System validates ownership/admin override gate.
3. System verifies course exists and is `ACTIVE`.
4. System sets course `status=ARCHIVED`, `archivedAt`, `archivedBy`.
5. System blocks new enrollment mutations for archived course.
6. System archives all `ACTIVE` assignments in the course as part of archive cascade policy.
7. System returns updated course DTO.

**Postconditions:**
- Course no longer appears in default active course lists.
- Historical records remain available via `includeArchived=true`.

**Errors:**
- `ARCH-UC-03-E1`: Course not found (`404`).
- `ARCH-UC-03-E2`: Teacher not owner (`403`).
- `ARCH-UC-03-E3`: Course already archived (`409`).

**Tests (representative):**
- `test_ARCH_UC_03_TEACHER_owner`
- `test_ARCH_UC_03_ADMIN_override`
- `test_ARCH_UC_03_E2`
- `test_ARCH_CN_05_archived_course_blocks_enrollment_mutations`
- `test_ARCH_CN_13_course_archive_cascades_assignments`
- `test_ARCH_CN_13_cascade_rollback_on_conflict`

---

### ARCH-UC-04 — Restore Archived Entity

**Roles:** Course restore: TEACHER (owner) or ADMIN; Assessment restore: ADMIN/RESEARCHER (FR-06 ASMT gate); Assignment restore: TEACHER (owner) or ADMIN  
**Endpoints:**
- `POST /api/v1/courses/{course_id}/restore`
- `POST /api/v1/assessments/{assessment_id}/restore`
- `POST /api/v1/assignments/{assignment_id}/restore`

**Main Flow:**
1. Caller requests restore.
2. System validates caller rights for entity type.
3. System verifies entity exists and `status=ARCHIVED`.
4. System checks restore preconditions (no conflicting parent state, no blocked dependency).
5. System sets `status=ACTIVE`, clears archival metadata fields as policy defines.
6. System returns updated DTO.

**Errors:**
- `ARCH-UC-04-E1`: Entity not found (`404`).
- `ARCH-UC-04-E2`: Unauthorized role (`403`).
- `ARCH-UC-04-E3`: Entity not archived (`409`).
- `ARCH-UC-04-E4`: Restore precondition failure (`409`).

**Tests (representative):**
- `test_ARCH_UC_04_restore_course`
- `test_ARCH_UC_04_restore_assessment`
- `test_ARCH_UC_04_restore_assignment`
- `test_ARCH_UC_04_E4_restore_blocked_by_parent_archive`
- `test_ARCH_CN_14_course_restore_does_not_restore_assignments`

---

### ARCH-UC-05 — List and Filter Archived Records

**Roles:** ADMIN, RESEARCHER, TEACHER (according to source-domain visibility)  
**Endpoints:** Existing list/detail endpoints with archive filters, e.g.:
- `GET /api/v1/courses?includeArchived=true`
- `GET /api/v1/assignments?includeArchived=true`
- `GET /api/v1/assessments?includeArchived=true`

**Main Flow:**
1. Caller requests list/detail.
2. Default behavior returns `ACTIVE` only.
3. If `includeArchived=true`, system includes archived rows only when caller has visibility rights for that resource.
4. Response includes `status` field for each record.

**Errors:**
- `ARCH-UC-05-E1`: Unauthorized archive visibility request (`403`).
- `ARCH-UC-05-E2`: Invalid filter value (`400`).

**Tests (representative):**
- `test_ARCH_UC_05_default_excludes_archived`
- `test_ARCH_UC_05_include_archived_for_admin`
- `test_ARCH_UC_05_teacher_scoped_archive_visibility`

---

### ARCH-UC-06 — Purge Archived Entity (Hard Delete)

**Roles:** ADMIN only  
**Endpoint pattern:** `DELETE /api/v1/{resource}/{id}?purge=true`

**Main Flow:**
1. Admin requests purge.
2. System verifies entity exists and `status=ARCHIVED`.
3. System evaluates purge eligibility:
   - retention threshold met,
   - no protected dependent records,
   - domain-specific purge guard passes.
4. If eligible, system hard-deletes entity.
5. Returns `204 No Content`.

**Errors:**
- `ARCH-UC-06-E1`: Caller not admin (`403`).
- `ARCH-UC-06-E2`: Entity not archived (`409`).
- `ARCH-UC-06-E3`: Dependency/retention rule violation (`409`).

**Tests (representative):**
- `test_ARCH_UC_06_admin_purge_success`
- `test_ARCH_UC_06_E2_not_archived_conflict`
- `test_ARCH_CN_07_purge_blocked_by_dependencies`

---

### ARCH-UC-07 — Audit Lifecycle Mutations

**Roles:** System behavior (all archive/restore/purge flows)  
**Trigger:** Any successful or denied lifecycle mutation attempt

**Main Flow:**
1. Service emits audit event with actor, action, target, before/after status, and outcome.
2. Audit record is persisted according to OBS policy.
3. Failure to persist audit log is handled per FR-11 rules (non-blocking unless policy changes).

**Tests (representative):**
- `test_ARCH_UC_07_archive_emits_audit`
- `test_ARCH_UC_07_restore_emits_audit`
- `test_ARCH_UC_07_purge_emits_audit`

---

## 5) Constraints

### ARCH-CN-01 — Common Lifecycle States
- ARCH-managed entities must expose `status` with values:
  - `ACTIVE`
  - `ARCHIVED`
- Optional internal state for purge workflow may be added later (`PENDING_PURGE`) but is not required for v1.
- Applies to: ARCH-UC-01..06.

### ARCH-CN-02 — Archive is Non-destructive
- Archive mutation must not delete user accounts, submissions, enrollments, or assessment answers.
- Archive only changes lifecycle metadata and write availability.
- Applies to: ARCH-UC-01..03.

### ARCH-CN-03 — Archived Assessment Blocks Assignment Creation
- Creating an assignment from an archived assessment returns `409`.
- Existing assignments are unaffected.
- Applies to: ARCH-UC-01.

### ARCH-CN-04 — Archived Assignment Blocks Student Writes
- When assignment status is `ARCHIVED`, draft save and submit endpoints reject write attempts with `409`.
- Read endpoints remain available according to role visibility.
- Applies to: ARCH-UC-02.

### ARCH-CN-05 — Archived Course Blocks Course Mutations
- No enrollment add/drop and no new assignment creation against archived course.
- Existing read operations remain available with archive filters.
- Applies to: ARCH-UC-03.

### ARCH-CN-06 — Default Read Filter is Active-only
- List endpoints default to `status=ACTIVE`.
- Archived rows are included only when `includeArchived=true`.
- Applies to: ARCH-UC-05.

### ARCH-CN-07 — Purge Eligibility Gate
- Purge requires `status=ARCHIVED`.
- Purge requires no protected dependents and retention eligibility.
- Failure returns `409` with explicit reason.
- Applies to: ARCH-UC-06.

### ARCH-CN-08 — Permission Matrix Consistency
- Archive/restore rights must follow source-domain ownership rules plus explicit admin overrides where defined.
- RESEARCHER remains read-focused unless source FR grants mutation rights.
- Applies to: ARCH-UC-01..04.

### ARCH-CN-09 — Audit Required for Lifecycle Mutations
- Archive, restore, and purge attempts must emit auditable records (success/failure/denied).
- Audit payload must include actor, target type/id, old/new status, timestamp.
- Applies to: ARCH-UC-07.

### ARCH-CN-10 — Error Semantics
- `403` for permission/ownership violations.
- `404` for unknown target.
- `409` for lifecycle conflicts (already archived, blocked restore, purge ineligible).
- `400` for malformed filter/query inputs.
- Applies to: ARCH-UC-01..06.

### ARCH-CN-11 — API Endpoint Pattern Consistency
- Archive endpoints use `POST /{resource}/{id}/archive`.
- Restore endpoints use `POST /{resource}/{id}/restore`.
- Purge stays explicit via `DELETE /{resource}/{id}?purge=true` (admin-only).
- Applies to: ARCH-UC-01..06.

### ARCH-CN-12 — Query and Index Requirements
- ARCH-managed tables must index `status` and timestamp fields used by list filters.
- Archive filters must be executed at DB layer, not in-memory.
- Applies to: ARCH-UC-05..06.

### ARCH-CN-13 — Course Archive Cascade Policy
- Archiving a course must cascade-archive all `ACTIVE` assignments in that course in the same transaction boundary.
- Cascade archive must not delete assignments or submissions.
- If any assignment cannot be archived due to state conflict, the course archive operation fails with `409` and no partial archive.
- Applies to: ARCH-UC-03.

### ARCH-CN-14 — Restore Preconditions and Non-cascade Policy
- Restore is blocked (`409`) when parent lifecycle state is incompatible:
  - Assignment cannot be restored while its course is archived.
  - Assignment cannot be restored while its source assessment is archived.
- Course restore restores the course only; cascade-archived assignments remain `ARCHIVED` and must be restored individually.
- Error response must include blocking dependency reason.
- Applies to: ARCH-UC-04.

---

## 6) Infrastructure Contract

### 6.1 Data Contract

Each ARCH-managed entity includes:

| Field | Type | Description |
|------|------|-------------|
| `status` | enum | `ACTIVE` or `ARCHIVED` |
| `archivedAt` | datetime nullable | Archive timestamp |
| `archivedBy` | FK nullable | User who archived |
| `restoredAt` | datetime nullable | Last restore timestamp (optional) |
| `restoredBy` | FK nullable | User who restored (optional) |

### 6.2 Endpoint Contract

| Method | Endpoint | Auth + visibility gate | Use Case |
|-------|----------|------------------------|----------|
| POST | `/api/v1/assessments/{assessment_id}/archive` | ASMT mutation gate | ARCH-UC-01 |
| POST | `/api/v1/assignments/{assignment_id}/archive` | Assignment ownership/admin override | ARCH-UC-02 |
| POST | `/api/v1/courses/{course_id}/archive` | Course ownership/admin override | ARCH-UC-03 |
| POST | `/api/v1/assessments/{assessment_id}/restore` | ASMT mutation gate | ARCH-UC-04 |
| POST | `/api/v1/assignments/{assignment_id}/restore` | Assignment ownership/admin override | ARCH-UC-04 |
| POST | `/api/v1/courses/{course_id}/restore` | Course ownership/admin override | ARCH-UC-04 |
| GET | Existing list endpoints + `includeArchived=true` | Source-domain read gate | ARCH-UC-05 |
| DELETE | Existing delete endpoint + `purge=true` (admin-only) | Admin + purge eligibility gate | ARCH-UC-06 |

### 6.3 Filter Contract

| Query Param | Type | Default | Notes |
|------------|------|---------|-------|
| `includeArchived` | boolean | `false` | Include archived rows in list results |
| `status` | string | `ACTIVE` | Optional explicit status filter |
| `purge` | boolean | `false` | Hard-delete intent flag; admin-only |

### 6.4 Audit Contract

Audit actions (FR-11) for ARCH:
- `ARCHIVE`
- `RESTORE`
- `PURGE`

Audit payload minimum:
- actor user id
- action
- target resource type/id
- `old_status`
- `new_status`
- outcome (`SUCCESS`, `FAILURE`, `DENIED`)
- timestamp

---

## 7) Error Model

ARCH errors are lifecycle and permission conflicts, not infrastructure failures.

| Scenario | Behavior | Contract |
|----------|----------|----------|
| Archive request for missing entity | Return not found | `404` |
| Archive by unauthorized role | Reject | `403` |
| Archive already archived entity | Reject idempotency conflict | `409` |
| Restore active entity | Reject invalid transition | `409` |
| Restore blocked by parent/archive dependency | Reject | `409` |
| Student submits to archived assignment | Reject write | `409` |
| Assignment creation on archived course/assessment | Reject write | `409` |
| Purge non-archived entity | Reject | `409` |
| Purge ineligible due to dependencies/retention | Reject + reason | `409` |
| Invalid archive filter query (`includeArchived=foo`) | Reject malformed input | `400` |

---

## 8) Test Strategy by Layer

### Naming Convention
- UC tests: `test_ARCH_UC_##[_ROLE|_E#]`
- Constraint tests: `test_ARCH_CN_##_*`
- System tests: `ST-ARCH-UC-##` / `ST-ARCH-CN-##`

### Backend Unit
- State transition helper tests (`ACTIVE -> ARCHIVED`, `ARCHIVED -> ACTIVE`).
- Permission matrix checks (owner/admin override).
- Purge eligibility evaluator.
- Archive filter query builder.

### Backend Integration
- API archive/restore/purge flows with role gating.
- Cross-domain effects:
  - archived assessment blocks assignment create,
  - archived assignment blocks submit/save,
  - archived course blocks enrollment mutations.
- Default active-only list behavior and `includeArchived=true`.
- Audit row creation for mutation attempts.

### System Tests (Black Box)
- `ST-ARCH-UC-01` archive assessment then verify assignment create fails.
- `ST-ARCH-UC-02` archive assignment then verify student submit fails.
- `ST-ARCH-UC-03` archive course then verify roster mutations blocked.
- `ST-ARCH-UC-04` restore entity and verify reads/writes resume.
- `ST-ARCH-UC-05` list filters hide/show archived as expected.
- `ST-ARCH-UC-06` purge only allowed for archived + eligible entities.
- `ST-ARCH-CN-09` audit entries exist for archive/restore/purge actions.

---

## 9) NFR Cross-References

- **Security**
  - Role/ownership-gated lifecycle mutations (ARCH-CN-08).
  - Explicit conflict/error semantics to prevent unsafe fallthrough (ARCH-CN-10).
- **Data Integrity**
  - Non-destructive archive semantics (ARCH-CN-02).
  - Purge dependency/retention guard (ARCH-CN-07).
- **Reliability**
  - Consistent lifecycle state machine and endpoint patterns (ARCH-CN-01, ARCH-CN-11).
- **Performance**
  - Indexed status filters and DB-level filtering (ARCH-CN-12).
- **Auditability**
  - Mandatory lifecycle audit events (ARCH-CN-09).

---

## 10) Cross-Domain References

| Domain | ARCH dependency | Integration note |
|--------|------------------|------------------|
| FR-05 CRS | Course status and enrollment mutation guards | Archived courses block roster mutations and new course-level writes. |
| FR-06 ASMT | Assessment archive lifecycle | Archived assessments cannot be used for new assignments. |
| FR-07 ASGN | Assignment archive lifecycle | Archived assignments stop student submission writes. |
| FR-08 SUB | Submission write/read behavior under archive | SUB endpoints must enforce assignment/course status gates on writes. |
| FR-09 VIZ | Visibility of archived entities in dashboards | VIZ should default to active-only unless explicit archive filter is enabled. |
| FR-10 EXP | Export behavior for archived data | Export endpoints must define whether archived rows are included by default or only with explicit filters. |
| FR-11 OBS | Lifecycle action auditing | Archive/restore/purge events must emit audit logs with status transitions. |
| FR-12 ENV | Profile-specific operational behavior | No profile-specific ARCH behavior required in v1. |
| FR-13 INFRA | Migrations/jobs support | ARCH adds schema migrations and optional purge jobs executed via infra tooling. |

---

## 11) Current Implementation Alignment Notes

1. **No cross-domain lifecycle spec exists today.** Archive semantics are currently scattered in FR-05/06/07/08 language and endpoint-specific logic.
2. **Unsafe hard-delete behavior exists in CRS paths.** Existing delete flows remove records destructively where archive should be preferred.
3. **Assessment archive endpoint not standardized.** FR-06 defines archive lifecycle but implementation routing/policy remains incomplete.
4. **Assignment archive behavior needs strict SUB gating.** FR-07 and FR-08 require blocking draft/save/submit on archived assignments, but enforcement is not centralized.
5. **List filters are inconsistent across domains.** `includeArchived` and `status` query behavior must be standardized.
6. **Purge policy is undefined in code.** No shared eligibility evaluator for retention/dependency checks exists yet.
7. **Audit integration is partial.** FR-11 defines audit model/action patterns; ARCH lifecycle actions need explicit wiring.
8. **No shared lifecycle utilities.** Transition validation, conflict responses, and status constants should be consolidated in reusable service helpers.
9. **Migration plan needed.** Add status and archival metadata fields where missing and backfill existing rows as `ACTIVE`.
10. **Test coverage gap.** ARCH UC/CN tests do not yet exist as a dedicated suite; currently only domain-local behavior is partially tested.
