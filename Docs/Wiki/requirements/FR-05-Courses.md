# FR-05 Courses and Enrollment Management (CRS) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | CRS |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER, STUDENT |
| **Related Issues** | TBD |
| **Dependencies** | FR-02 REG (code-gated student registration), FR-04 USER (student account lifecycle), FR-14 ARCH (archive lifecycle) |

---

## 1) Scope

### In Scope
- Course lifecycle for teacher-owned courses:
  - create course
  - list accessible courses
  - read course detail
  - edit course
  - delete course
- Course roster management:
  - list enrolled students
  - add one student to a course
  - remove (drop) a student from a course
- Authorization matrix for course visibility and management:
  - ADMIN/RESEARCHER global read visibility
  - TEACHER ownership-based management
- Enrollment lifecycle semantics (`ACTIVE`, `DROPPED`) and default filtering behavior.
- Data integrity protections for multi-course student membership.

### Out of Scope
- Bulk student import/create endpoints (removed from FR-05 contract).
- Self-registration and course join by code (FR-02).
- User account lifecycle as a standalone domain (FR-04).
- Assignment/submission authoring and grading flows (FR-06/FR-07/FR-08).
- Course data archive/export system (future requirement dependency; see CRS-CN-12).
- UI wireframes and future browser smoke flows (tracked separately).

### Core Intent
- Provide teacher-owned course lifecycle with ownership-bounded CRUD operations.
- Enforce enrollment lifecycle semantics (ACTIVE/DROPPED) with data integrity protections.
- Maintain authorization matrix for course visibility across privileged roles.

---

## 2) Actors

| Role | Type | CRS domain permissions |
|------|------|-------------------------|
| ADMIN | System role (`is_staff=True`) | Read-only visibility across all courses and rosters; no teacher-owned write actions |
| RESEARCHER | User role | Read-only visibility across all courses and rosters; no teacher-owned write actions |
| TEACHER | User role | Create/manage own courses; manage own roster |
| STUDENT | User role | No direct CRS write operations |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER > STUDENT

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| CRS-US-01 | TEACHER | As a teacher I can create courses I own so I can organize assignments and students. |
| CRS-US-02 | ADMIN, RESEARCHER, TEACHER | As a privileged user I can view courses I am allowed to see so that dashboards and oversight views are accurate. |
| CRS-US-03 | TEACHER | As a teacher I can rename or delete my own courses when class structure changes. |
| CRS-US-04 | TEACHER | As a teacher I can add a student to a specific course from roster management. |
| CRS-US-05 | TEACHER | As a teacher I can drop a student from my course without deleting their global account. |
| CRS-US-06 | ADMIN, RESEARCHER, TEACHER | As a privileged user I can view a course roster with active enrollments only by default. |

---

## 4) Use Cases

### CRS-UC-01 — Create Course

**Roles:** TEACHER  
**Endpoint:** `POST /api/v1/courses`

**Main Flow:**
1. Teacher submits `name`.
2. System validates teacher profile exists.
3. System creates course owned by requesting teacher.
4. Returns course DTO.

**Errors:**
- `CRS-UC-01-E1`: Missing/invalid name.
- `CRS-UC-01-E2`: Caller is not a teacher.
- `CRS-UC-01-E3`: Teacher profile missing.

**Tests (representative):**
- `test_CRS_UC_01_TEACHER`
- `test_CRS_UC_01_E2`

---

### CRS-UC-02 — List Accessible Courses

**Roles:** ADMIN, RESEARCHER, TEACHER  
**Endpoint:** `GET /api/v1/courses`

**Main Flow:**
1. Caller requests course list.
2. System applies visibility matrix:
   - ADMIN/RESEARCHER: all courses
   - TEACHER: own courses only
3. Returns paginated course DTO list.

**Errors:**
- `CRS-UC-02-E1`: Unauthorized role.

**Tests (representative):**
- `test_CRS_UC_02_RESEARCHER`
- `test_CRS_UC_02_TEACHER`

---

### CRS-UC-03 — Get Course Detail

**Roles:** ADMIN, RESEARCHER, TEACHER  
**Endpoint:** `GET /api/v1/courses/{course_id}`

**Main Flow:**
1. System resolves course by ID.
2. System checks `can_view_course`.
3. Returns course DTO.

**Errors:**
- `CRS-UC-03-E1`: Course not found.
- `CRS-UC-03-E2`: Forbidden by visibility matrix.

**Tests (representative):**
- `test_CRS_UC_03_TEACHER`
- `test_CRS_UC_03_E1`

---

### CRS-UC-04 — Update Course

**Roles:** TEACHER (owner only)  
**Endpoint:** `PATCH /api/v1/courses/{course_id}`

**Main Flow:**
1. System resolves course by ID.
2. System checks ownership (`can_manage_course`).
3. Validates patch payload (`name`).
4. Saves update and returns course DTO.

**Errors:**
- `CRS-UC-04-E1`: Course not found.
- `CRS-UC-04-E2`: Forbidden (not owner).
- `CRS-UC-04-E3`: Invalid name payload.

**Tests (representative):**
- `test_CRS_UC_04_TEACHER`
- `test_CRS_UC_04_E1`

---

### CRS-UC-05 — Delete Course

**Roles:** TEACHER (owner only)  
**Endpoint:** `DELETE /api/v1/courses/{course_id}`

**Main Flow:**
1. System resolves course by ID.
2. System checks ownership (`can_manage_course`).
3. System checks whether archival capability required by `CRS-CN-12` is available.
4. If archival is unavailable, request is rejected with `409 Conflict`.
5. If archival is available, system archives course submission data into a retrievable package.
6. Removes course and course-scoped enrollment records.
7. Returns `204 No Content`.

**Policy Requirements:**
- Course deletion must **not** delete student `User` accounts.
- Course deletion is **blocked** until archival capability is implemented (`CRS-CN-12`).

**Errors:**
- `CRS-UC-05-E1`: Course not found.
- `CRS-UC-05-E2`: Forbidden (not owner).
- `CRS-UC-05-E3`: Deletion blocked because archival capability is unavailable.

**Tests (representative):**
- `test_CRS_UC_05_TEACHER`
- `test_CRS_CN_05`

---

### CRS-UC-06 — List Students in Course

**Roles:** ADMIN, RESEARCHER, TEACHER  
**Endpoint:** `GET /api/v1/courses/{course_id}/students`

**Main Flow:**
1. System resolves course by ID.
2. System checks `can_view_course`.
3. Returns paginated roster DTOs.
4. Default behavior includes `ACTIVE` enrollments only.

**Errors:**
- `CRS-UC-06-E1`: Course not found.
- `CRS-UC-06-E2`: Forbidden by visibility matrix.

**Tests (representative):**
- `test_CRS_UC_06_TEACHER`
- `test_CRS_CN_04`

---

### CRS-UC-07 — Add One Student to Course

**Roles:** TEACHER (owner only)  
**Canonical Endpoint:** `POST /api/v1/courses/{course_id}/students`

**Main Flow:**
1. Teacher submits student create payload (`name`, optional `consent`, optional `password`).
2. System enforces system-managed username rules.
3. System creates a new student account with system-managed username.
4. System creates course enrollment with `ACTIVE` status.
5. System creates any required placeholder submissions.
6. Returns student enrollment DTO.

**Errors:**
- `CRS-UC-07-E1`: Invalid payload.
- `CRS-UC-07-E2`: Course not found.
- `CRS-UC-07-E3`: Forbidden (not owner).
- `CRS-UC-07-E4`: Duplicate active enrollment.
- `CRS-UC-07-E5`: Client attempts to set username.

**Tests (representative):**
- `test_CRS_UC_07_TEACHER`
- `test_CRS_UC_07_E1`
- `test_CRS_CN_09`

---

### CRS-UC-08 — Remove Student from Course

**Roles:** TEACHER (owner only)  
**Endpoint:** `DELETE /api/v1/courses/{course_id}/students/{student_user_id}`

**Main Flow:**
1. System resolves course and target student enrollment.
2. System checks ownership (`can_manage_course`).
3. System sets enrollment status to `DROPPED` (enrollment record is preserved for archive traceability).
4. Returns `204 No Content`.

**Policy Requirement:** Removing from one course must not delete global user identity.

**Errors:**
- `CRS-UC-08-E1`: Course not found.
- `CRS-UC-08-E2`: Enrollment/student not found for course.
- `CRS-UC-08-E3`: Forbidden (not owner).

**Tests (representative):**
- `test_CRS_UC_08_TEACHER`
- `test_CRS_UC_08_E2`
- `test_CRS_CN_06`

---

## 5) Constraints

### CRS-CN-01 — Course Ownership Boundary
- Only owning teacher can patch/delete course or modify roster.
- Applies to: CRS-UC-04, CRS-UC-05, CRS-UC-07, CRS-UC-08.

### CRS-CN-02 — Course Visibility Matrix
- ADMIN and RESEARCHER can read all courses/rosters; TEACHER can read own only.
- Applies to: CRS-UC-02, CRS-UC-03, CRS-UC-06.

### CRS-CN-03 — No Bulk Student Import
- Bulk student add endpoint is not part of FR-05 contract.
- Applies to: CRS-UC-07.

### CRS-CN-04 — Active-Only Roster
- Student roster endpoints return `ACTIVE` enrollments only. Dropped students are never included in roster responses.
- Applies to: CRS-UC-06.

### CRS-CN-05 — No User Deletion Side Effects
- Course delete must not delete `User` accounts and must archive submission data before removing course records (per CRS-CN-12 dependency).
- Student removal (DROPPED) must not delete `User` accounts or submission history.
- Applies to: CRS-UC-05, CRS-UC-08.

### CRS-CN-06 — Multi-Course Membership Safety
- Student removal from one course must not affect enrollments in other courses.
- Applies to: CRS-UC-08.

### CRS-CN-07 — Enrollment Uniqueness
- One enrollment per `(course, student_profile)`.
- Applies to: CRS-UC-07.

### CRS-CN-08 — ID-Based Path Contract
- Course/student resource paths use numeric IDs.
- Applies to: CRS-UC-03, CRS-UC-04, CRS-UC-05, CRS-UC-06, CRS-UC-08.

### CRS-CN-09 — System-Managed Student Username
- Caller cannot override student username during course add flow.
- Applies to: CRS-UC-07.

### CRS-CN-10 — Atomic Enrollment Provisioning
- Enrollment creation and submission placeholder generation are atomic.
- Applies to: CRS-UC-07.

### CRS-CN-11 — Enrollment Lifecycle Uses Status
- `DROPPED` is the sole removal mechanism for students from courses. No enrollment hard-deletes.
- `ACTIVE` and `DROPPED` are operational states enforced by service layer, not dead enum values.
- Applies to: CRS-UC-06, CRS-UC-08.

### CRS-CN-12 — Course Deletion Requires Data Archival
- Course deletion must not proceed until submission data (answers, images, metadata) has been archived into a retrievable package accessible to researchers.
- Depends on: future archive/export requirement. Course deletion returns `409 Conflict` until archival support is implemented.
- Applies to: CRS-UC-05.

---

## 6) Infrastructure Contract

### 6.1 Endpoint Contract

| Method | Path | Auth | UC |
|--------|------|------|-----|
| GET | `/api/v1/courses` | IsTeacherOrAbove | CRS-UC-02 |
| POST | `/api/v1/courses` | IsTeacherOrAbove + teacher gate | CRS-UC-01 |
| GET | `/api/v1/courses/{course_id}` | IsTeacherOrAbove | CRS-UC-03 |
| PATCH | `/api/v1/courses/{course_id}` | IsTeacherOrAbove + ownership gate | CRS-UC-04 |
| DELETE | `/api/v1/courses/{course_id}` | IsTeacherOrAbove + ownership gate | CRS-UC-05 |
| GET | `/api/v1/courses/{course_id}/students` | IsTeacherOrAbove + visibility gate | CRS-UC-06 |
| POST | `/api/v1/courses/{course_id}/students` | IsTeacher + ownership gate | CRS-UC-07 |
| DELETE | `/api/v1/courses/{course_id}/students/{student_user_id}` | IsTeacher + ownership gate | CRS-UC-08 |

**Deprecations (not part of target FR-05 contract):**
- `POST /api/v1/students`
- `POST /api/v1/students/bulk`
- Deprecation policy: deprecated now; remove after migration in the next FR-05 implementation release.

---

## 7) Error Model

Standard error payload:
- `{"detail": "<message>"}` for validation, not-found, or authorization errors.

Expected statuses by UC:
- `400`: invalid payload/business rule violation
- `403`: forbidden by role or ownership
- `404`: target course/enrollment not found
- `409`: operation blocked by unmet archival dependency (`CRS-UC-05-E3`)
- `201`: create success
- `200`: read/update success
- `204`: delete/drop success

---

## 8) Test Strategy by Layer

### Backend Unit
- Ownership, visibility, lifecycle, and mutation behavior:
  - `can_view_course`, `can_manage_course`
  - enrollment lifecycle (`ACTIVE`/`DROPPED`)
  - no-user-delete invariants on course/roster mutations

### Backend Integration
- Route + auth + serializer + persistence:
  - `tests/integration/test_courses_routes.py`
  - additional FR-05 traceability tests for CRS-CN-03/04/05/06/11

### Frontend Unit/Integration
- Deferred for FR-05 UI implementation phase; backend contract is source of truth for now.

### System Tests (Black Box)
- `ST-CRS-UC-01` through `ST-CRS-UC-08`
- Required constraint checks:
  - `ST-CRS-CN-05` (course delete does not delete users)
  - `ST-CRS-CN-06` (multi-course membership safe)
  - `ST-CRS-CN-11` (dropped lifecycle semantics observable)

---

## 9) NFR Cross-References

- **NFR-Security**
  - Ownership and role gates enforced server-side.
  - No identity deletion side-effects from course operations.
- **NFR-Reliability**
  - Enrollment and dependent provisioning are transactional.
  - Deterministic status codes and error payloads.
- **NFR-Performance**
  - Paginated course and roster listing.
  - Query paths avoid unbounded response payloads.
- **NFR-Maintainability**
  - Course domain behavior centralized in service/query helpers.
  - Explicit lifecycle semantics (`ACTIVE`/`DROPPED`) avoid hidden behavior.

---

## 10) Cross-Domain References

| Domain | CRS dependency | Integration note |
|--------|----------------|------------------|
| FR-02 REG | Code-gated student registration creates accounts enrolled via CRS | Registration flow may trigger enrollment; shared student identity |
| FR-04 USER | Student account lifecycle | CRS enrollment references User accounts; drop does not delete user (CRS-CN-05) |
| FR-07 ASGN | Assignment creation requires course ownership | ASGN-UC-01 validates `can_manage_course` from CRS-CN-01 |
| FR-08 SUB | Submission provisioning at enrollment | CRS-UC-07 creates placeholder submissions for enrolled students |
| FR-14 ARCH | Course archive lifecycle | ARCH-UC-03 archives courses; CRS-CN-12 requires data archival before deletion |

---

## 11) Current Implementation Alignment Notes

This draft defines the target FR-05 contract. Current code has known deltas that must be resolved before FR-05 can be marked COMPLETE:

1. Remove bulk student endpoint and service path.
2. Eliminate student `User` hard-deletion in course/roster mutations.
3. Enforce active-only roster filtering (no query param for dropped).
4. Switch student removal from hard-delete to `DROPPED` status flip.
5. Align route/docstring contracts with canonical endpoint table above.
6. Add missing FR-05 traceability tests for constraints and error paths.
7. Implement archive/export dependency required by `CRS-CN-12` to unlock course deletion path.
