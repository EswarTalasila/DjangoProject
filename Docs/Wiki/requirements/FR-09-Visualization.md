# FR-09 Visualization (VIZ) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | VIZ |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER |
| **Related Issues** | #28 (Role Separation), #31 (API REST Standardization) |
| **Dependencies** | FR-03 SUDO (`VIEW_IDENTIFIABLE_VIZ` permission), FR-05 CRS (course ownership), FR-06 ASMT (assessment metadata, `GradingMode.MOOD_METER`), FR-08 SUB (submission data source) |

---

## 1) Scope

### In Scope
- Backend-computed aggregate endpoints for dashboard visualization:
  - Teacher dashboard overview: course-level summary cards.
  - Course drill-down: per-assignment completion and grade stats.
  - Assignment drill-down: grade distribution (average, median, high, low, histogram).
  - Mood meter: quadrant distribution for mood meter assignments.
- Read-only data aggregation — no mutations.
- Role-gated access: `IsTeacherOrAbove` (TEACHER, RESEARCHER, ADMIN); students excluded.
- Researcher anonymization: identifiable fields omitted unless researcher holds `VIEW_IDENTIFIABLE_VIZ` sudo permission.
- Query param filtering: `startDate`, `endDate`, `category`, `assessmentId` where applicable.
- Client-side chart rendering: backend returns computed numbers, frontend renders with Recharts + custom mood meter grid component.

### Out of Scope
- Raw submission data dumps (FR-08 SUB endpoints serve this purpose).
- Individual student answer viewing (FR-08 SUB-UC-04, SUB-UC-05).
- Data export to CSV/PDF (FR-10 EXP).
- Mood meter frontend visualization UX is temporarily deferred; backend mood meter aggregate endpoint remains available.
- Assessment template management (FR-06 ASMT).
- Assignment lifecycle (FR-07 ASGN).
- Student-facing dashboards (students cannot access VIZ endpoints).
- Server-side chart/image/SVG generation.
- Trend-over-time charts (future enhancement; current spec covers point-in-time aggregates).
- Wireframes and Playwright E2E scripts (tracked separately).

### Removals
- `POST /api/v1/visualization/` — current raw-data endpoint. This endpoint returns raw `VisualizationSubmissionDTO` arrays and is replaced entirely by the aggregate endpoints defined in this spec. To be removed when FR-09 aggregate endpoints are implemented. Raw submission data remains available through FR-08 SUB endpoints (`GET /api/v1/assignments/{id}/submissions`, `GET /api/v1/students/{id}/submissions`, etc.).
- `VisualizationFilterSerializer` — current serializer with dead params (`teacherId`, `isMoodMeter`). Replaced by query param validation on new endpoints.
- `VisualizationSubmissionDTO` — current DTO in `core/dtos.py`. No longer needed; aggregate endpoints return summary objects, not submission records.

---

## 2) Actors

| Role | Type | VIZ domain permissions |
|------|------|------------------------|
| ADMIN | System role (`is_staff=True`) | Full read access to all visualization data across all courses; identifiable data visible |
| RESEARCHER | User role | Read access to all visualization data across all courses; identifiable data requires `VIEW_IDENTIFIABLE_VIZ` sudo permission (see VIZ-CN-01) |
| TEACHER | User role | Read access to visualization data for own courses only; identifiable data visible for own courses |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER

> **STUDENT excluded:** Students cannot access any VIZ endpoint. `IsTeacherOrAbove` permission rejects student requests with `403 Forbidden`.

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| VIZ-US-01 | TEACHER | As a teacher I can view a dashboard with summary cards for all my courses so that I can get a quick overview of enrollment, completion rates, and grades. |
| VIZ-US-02 | TEACHER | As a teacher I can drill into a course to see per-assignment completion and grade summaries so that I can identify which assignments need attention. |
| VIZ-US-03 | TEACHER | As a teacher I can view grade distribution for a specific assignment so that I can understand how students performed and identify struggling students. |
| VIZ-US-04 | TEACHER | As a teacher I can view mood meter quadrant distribution for a mood meter assignment so that I can understand the emotional state of my class. |
| VIZ-US-05 | RESEARCHER | As a researcher I can view anonymized aggregate data across all courses so that I can conduct cross-cohort analysis without accessing student-identifying information. |
| VIZ-US-06 | RESEARCHER | As a researcher with `VIEW_IDENTIFIABLE_VIZ` sudo permission I can view full identifiable aggregate data across all courses so that I can conduct detailed research with appropriate authorization. |
| VIZ-US-07 | ADMIN | As an admin I can view visualization data for any course or assignment so that I can monitor system-wide academic activity. |

---

## 4) Use Cases

### VIZ-UC-01 — Teacher Dashboard Overview

**Roles:** ADMIN, RESEARCHER, TEACHER
**Endpoint:** `GET /api/v1/visualizations/dashboard`

**Main Flow:**
1. Caller requests dashboard overview.
2. System validates caller has TEACHER or above role via `IsTeacherOrAbove`.
3. System determines course scope based on caller role:
   - TEACHER: courses owned by the caller (`course.teacher_profile == user.teacher_profile`).
   - RESEARCHER: all courses in the system.
   - ADMIN: all courses in the system.
4. For each course in scope, system computes:
   - `enrolledCount`: total enrollments with status `ACTIVE`.
   - `activeEnrollments`: enrollments with status `ACTIVE` (same as `enrolledCount` unless inactive enrollments are counted separately).
   - `assignmentCount`: total assignments linked to this course.
   - `avgCompletionRate`: `(submissions with status SUBMITTED or GRADED) / (assignmentCount × enrolledCount)`. Returns `null` if denominator is 0.
   - `avgScore`: average `score` across all `GRADED` submissions in this course. Returns `null` if no graded submissions exist.
   - `pendingGrades`: count of submissions with status `SUBMITTED` (awaiting manual grading).
5. System applies anonymization rules (VIZ-CN-01): if caller is RESEARCHER without `VIEW_IDENTIFIABLE_VIZ`, strip identifiable fields.
6. Returns `200 OK` with response body.

**Response:**
```json
{
  "generatedAt": "2026-02-28T14:30:00Z",
  "courses": [
    {
      "courseId": 5,
      "courseName": "Art 101",
      "enrolledCount": 30,
      "activeEnrollments": 28,
      "assignmentCount": 8,
      "avgCompletionRate": 0.85,
      "avgScore": 78.3,
      "pendingGrades": 4
    }
  ]
}
```

> **Anonymized response** (RESEARCHER without `VIEW_IDENTIFIABLE_VIZ`): `courseId` and `courseName` fields are omitted entirely. The `courses` array contains summary objects with only numeric aggregate fields (`enrolledCount`, `activeEnrollments`, `assignmentCount`, `avgCompletionRate`, `avgScore`, `pendingGrades`).

**Errors:**
- `VIZ-UC-01-E1`: Caller is a student (`403 Forbidden` via `IsTeacherOrAbove`).
- `VIZ-UC-01-E2`: Unauthenticated request (`401 Unauthorized`).

**Tests (representative):**
- `test_VIZ_UC_01_ADMIN`
- `test_VIZ_UC_01_RESEARCHER`
- `test_VIZ_UC_01_RESEARCHER_anonymized`
- `test_VIZ_UC_01_TEACHER`
- `test_VIZ_CN_01_anonymization`

---

### VIZ-UC-02 — Course Summary

**Roles:** ADMIN, RESEARCHER, TEACHER
**Endpoint:** `GET /api/v1/visualizations/courses/{courseId}/summary`
**Query Params:** `startDate` (ISO date, optional), `endDate` (ISO date, optional), `category` (string, optional), `assessmentId` (int, optional)

**Main Flow:**
1. System resolves course by `courseId`.
2. System validates caller has TEACHER or above role via `IsTeacherOrAbove`.
3. System validates caller access:
   - TEACHER: must own the course (`course.teacher_profile == user.teacher_profile`).
   - RESEARCHER / ADMIN: can access any course.
4. System queries assignments linked to this course.
5. If `startDate` / `endDate` provided, filter assignments by `open_at` within the date range.
6. If `category` provided, filter to assignments whose assessment has matching category.
7. If `assessmentId` provided, filter to assignments linked to that assessment.
8. For each matching assignment, system computes:
   - `submittedCount`: submissions with status `SUBMITTED` or `GRADED`.
   - `totalStudents`: active enrollments in the course.
   - `completionPct`: `submittedCount / totalStudents`. Returns `null` if `totalStudents` is 0.
   - `gradedCount`: submissions with status `GRADED`.
   - `avgScore`: average `score` across `GRADED` submissions for this assignment. Returns `null` if no graded submissions.
   - `pendingGrades`: submissions with status `SUBMITTED` (awaiting grading).
9. System applies anonymization rules (VIZ-CN-01).
10. Returns `200 OK` with response body.

**Response:**
```json
{
  "generatedAt": "2026-02-28T14:30:00Z",
  "filters": { "startDate": null, "endDate": null, "category": null, "assessmentId": null },
  "courseId": 5,
  "courseName": "Art 101",
  "enrolledCount": 30,
  "assignments": [
    {
      "assignmentId": 12,
      "assessmentTitle": "Midterm",
      "assessmentCategory": "math",
      "submittedCount": 25,
      "totalStudents": 30,
      "completionPct": 0.83,
      "gradedCount": 22,
      "avgScore": 81.2,
      "pendingGrades": 3
    }
  ]
}
```

> **Anonymized response:** `courseId`, `courseName`, `assignmentId`, and `assessmentTitle` are omitted. `assessmentCategory` is retained (non-identifying).

**Errors:**
- `VIZ-UC-02-E1`: Course not found (`404 Not Found`).
- `VIZ-UC-02-E2`: Teacher does not own the course (`403 Forbidden`).
- `VIZ-UC-02-E3`: Caller is a student (`403 Forbidden` via `IsTeacherOrAbove`).
- `VIZ-UC-02-E4`: Unauthenticated request (`401 Unauthorized`).
- `VIZ-UC-02-E5`: Invalid query param type (`400 Bad Request`).

**Tests (representative):**
- `test_VIZ_UC_02_ADMIN`
- `test_VIZ_UC_02_RESEARCHER_anonymized`
- `test_VIZ_UC_02_TEACHER`
- `test_VIZ_UC_02_TEACHER_filter_by_category`
- `test_VIZ_UC_02_TEACHER_filter_by_date_range`

---

### VIZ-UC-03 — Assignment Grade Summary

**Roles:** ADMIN, RESEARCHER, TEACHER
**Endpoint:** `GET /api/v1/visualizations/assignments/{assignmentId}/summary`
**Query Params:** `startDate` (ISO date, optional), `endDate` (ISO date, optional)

**Main Flow:**
1. System resolves assignment by `assignmentId`.
2. System validates caller has TEACHER or above role via `IsTeacherOrAbove`.
3. System validates caller access:
   - TEACHER: must own the assignment's course (`assignment.course.teacher_profile == user.teacher_profile`).
   - RESEARCHER / ADMIN: can access any assignment.
4. System queries submissions for this assignment.
5. If `startDate` / `endDate` provided, filter submissions by `submitted_at` within the date range.
6. System computes aggregate stats from `GRADED` submissions:
   - `totalStudents`: active enrollments in the assignment's course.
   - `submittedCount`: submissions with status `SUBMITTED` or `GRADED`.
   - `gradedCount`: submissions with status `GRADED`.
   - `completionPct`: `submittedCount / totalStudents`. Returns `null` if `totalStudents` is 0.
   - `avgScore`: average of `score` across `GRADED` submissions. Returns `null` if no graded submissions.
   - `medianScore`: median of `score` across `GRADED` submissions. Returns `null` if no graded submissions.
   - `highScore`: maximum `score` across `GRADED` submissions. Returns `null` if no graded submissions.
   - `lowScore`: minimum `score` across `GRADED` submissions. Returns `null` if no graded submissions.
7. System computes `distribution`: scores are rounded to the nearest integer before binning. Bins are inclusive ranges: `0–59`, `60–69`, `70–79`, `80–89`, `90–100`. Each bin contains a `count` of graded submissions falling in that range.
8. System applies anonymization rules (VIZ-CN-01).
9. Returns `200 OK` with response body.

**Response:**
```json
{
  "generatedAt": "2026-02-28T14:30:00Z",
  "filters": { "startDate": null, "endDate": null },
  "assignmentId": 12,
  "assessmentTitle": "Midterm",
  "assessmentCategory": "math",
  "totalStudents": 30,
  "submittedCount": 25,
  "gradedCount": 22,
  "completionPct": 0.83,
  "avgScore": 81.2,
  "medianScore": 85.0,
  "highScore": 100.0,
  "lowScore": 45.0,
  "distribution": [
    { "range": "0-59", "count": 2 },
    { "range": "60-69", "count": 3 },
    { "range": "70-79", "count": 5 },
    { "range": "80-89", "count": 7 },
    { "range": "90-100", "count": 5 }
  ]
}
```

> **Anonymized response:** `assignmentId` and `assessmentTitle` are omitted. `assessmentCategory`, all numeric stats, and `distribution` are retained.

**Errors:**
- `VIZ-UC-03-E1`: Assignment not found (`404 Not Found`).
- `VIZ-UC-03-E2`: Teacher does not own the assignment's course (`403 Forbidden`).
- `VIZ-UC-03-E3`: Caller is a student (`403 Forbidden` via `IsTeacherOrAbove`).
- `VIZ-UC-03-E4`: Unauthenticated request (`401 Unauthorized`).
- `VIZ-UC-03-E5`: Invalid query param type (`400 Bad Request`).

**Tests (representative):**
- `test_VIZ_UC_03_ADMIN`
- `test_VIZ_UC_03_RESEARCHER_anonymized`
- `test_VIZ_UC_03_TEACHER`
- `test_VIZ_UC_03_TEACHER_filter_by_date_range`
- `test_VIZ_CN_02_distribution_bins`
- `test_VIZ_CN_02_null_scores`

---

### VIZ-UC-04 — Mood Meter Summary

**Roles:** ADMIN, RESEARCHER, TEACHER
**Endpoint:** `GET /api/v1/visualizations/assignments/{assignmentId}/mood-meter`

**Main Flow:**
1. System resolves assignment by `assignmentId`.
2. System validates caller has TEACHER or above role via `IsTeacherOrAbove`.
3. System validates the assignment's assessment has `grading_mode=GradingMode.MOOD_METER`. If not, return `409 Conflict` with generic message (VIZ-CN-04).
4. System validates caller access:
   - TEACHER: must own the assignment's course.
   - RESEARCHER / ADMIN: can access any assignment.
5. System queries all `GRADED` submissions for this assignment.
6. For each submission, system reads the mood meter answer's `row` (energy axis) and `col` (pleasantness axis) to determine quadrant placement:
   - High Energy / Positive (high row, high col)
   - High Energy / Negative (high row, low col)
   - Low Energy / Positive (low row, high col)
   - Low Energy / Negative (low row, low col)
7. System aggregates quadrant counts and percentages.
8. System applies anonymization rules (VIZ-CN-01). Mood meter data is inherently aggregate; no student-identifying fields are present in the response.
9. Returns `200 OK` with response body.

**Response:**
```json
{
  "generatedAt": "2026-02-28T14:30:00Z",
  "assignmentId": 12,
  "totalResponses": 28,
  "quadrants": [
    { "label": "High Energy / Positive", "count": 12, "pct": 0.43 },
    { "label": "High Energy / Negative", "count": 5, "pct": 0.18 },
    { "label": "Low Energy / Positive", "count": 8, "pct": 0.29 },
    { "label": "Low Energy / Negative", "count": 3, "pct": 0.11 }
  ]
}
```

> **Anonymized response:** `assignmentId` is omitted. Quadrant data is inherently anonymous (aggregate counts only).

**Errors:**
- `VIZ-UC-04-E1`: Assignment not found (`404 Not Found`).
- `VIZ-UC-04-E2`: Assignment's assessment is not a mood meter type (`409 Conflict`; response: `{"detail": "Incompatible assessment type"}`). Generic message to prevent assessment type enumeration.
- `VIZ-UC-04-E3`: Teacher does not own the assignment's course (`403 Forbidden`).
- `VIZ-UC-04-E4`: Caller is a student (`403 Forbidden` via `IsTeacherOrAbove`).
- `VIZ-UC-04-E5`: Unauthenticated request (`401 Unauthorized`).

**Tests (representative):**
- `test_VIZ_UC_04_ADMIN`
- `test_VIZ_UC_04_RESEARCHER`
- `test_VIZ_UC_04_TEACHER`
- `test_VIZ_CN_04_non_mood_meter_409`

---

## 5) Constraints

### VIZ-CN-01 — Researcher Anonymization via Sudo

- Researchers without `VIEW_IDENTIFIABLE_VIZ` sudo permission receive anonymized responses where identifiable fields are **omitted entirely** (not nulled, not replaced with opaque tokens).
- Identifiable fields subject to omission: `courseId`, `courseName`, `assignmentId`, `assessmentTitle`, `studentId`, `teacherId`.
- Non-identifiable fields always retained: all numeric aggregates (`enrolledCount`, `avgScore`, `completionPct`, etc.), `assessmentCategory`, `distribution`, quadrant data.
- Authorization check: `has_sudo_permission(user, SudoPermission.VIEW_IDENTIFIABLE_VIZ)` from FR-03.
- Access matrix:
  - TEACHER: identifiable data for own courses only (course ownership gate, not sudo).
  - ADMIN: identifiable data everywhere (admin bypasses sudo check).
  - RESEARCHER + `VIEW_IDENTIFIABLE_VIZ`: identifiable data everywhere.
  - RESEARCHER without `VIEW_IDENTIFIABLE_VIZ`: anonymized data everywhere.
- Applies to: VIZ-UC-01 through VIZ-UC-04.

### VIZ-CN-02 — Distribution Bin Rules

- Grade distribution bins use inclusive integer ranges: `0–59`, `60–69`, `70–79`, `80–89`, `90–100`.
- Scores are rounded to the nearest integer before binning (`round(score)`).
- A score of exactly `59.5` rounds to `60` and falls in the `60–69` bin.
- Bins always appear in the response even if their count is `0`.
- Scores outside `0–100` range: scores < 0 fall in `0–59`; scores > 100 fall in `90–100`. (Bonus points from SUB-CN-05 may produce scores > 100.)
- Applies to: VIZ-UC-03.

### VIZ-CN-03 — Teacher Course Ownership Gate

- Teachers can only access VIZ data for courses they own. Cross-teacher data access is prohibited.
- Ownership check: `course.teacher_profile == user.teacher_profile` (from FR-05 `CRS-CN-01`).
- For assignment-level endpoints (VIZ-UC-03, VIZ-UC-04): ownership is checked via `assignment.course.teacher_profile`.
- RESEARCHER and ADMIN bypass this check entirely.
- Applies to: VIZ-UC-01 through VIZ-UC-04.

### VIZ-CN-04 — Mood Meter Assessment Type Gate

- The `/mood-meter` endpoint (VIZ-UC-04) requires the assignment's assessment to have `grading_mode=GradingMode.MOOD_METER`.
- If the assessment uses any other grading mode, the endpoint returns `409 Conflict` with `{"detail": "Incompatible assessment type"}`.
- The error message is intentionally generic to prevent assessment type enumeration.
- Applies to: VIZ-UC-04.

### VIZ-CN-05 — Null Safety for Aggregates

- `avgScore`, `medianScore`, `highScore`, `lowScore`: return `null` when no `GRADED` submissions exist for the target scope. Prevents divide-by-zero and misleading `0` values.
- `avgCompletionRate` / `completionPct`: return `null` when the denominator is 0 (no enrollments or no assignments).
- Applies to: VIZ-UC-01, VIZ-UC-02, VIZ-UC-03.

### VIZ-CN-06 — Completion Rate Denominators

- Denominators are defined per-endpoint for clarity:
  - **Dashboard** (`avgCompletionRate`): `(total submissions with status >= SUBMITTED across all assignments in the course) / (assignmentCount × enrolledCount)`.
  - **Course summary** (`completionPct` per assignment): `(submissions for this assignment with status >= SUBMITTED) / (enrolledCount for the course)`.
  - **Assignment summary** (`completionPct`): `(submissions for this assignment with status >= SUBMITTED) / (totalStudents = active enrollments in the course)`.
- "Status >= SUBMITTED" means `SUBMITTED` or `GRADED` (excludes `NOT_STARTED` and `IN_PROGRESS`).
- Applies to: VIZ-UC-01, VIZ-UC-02, VIZ-UC-03.

### VIZ-CN-07 — Response Traceability

- Every VIZ endpoint response includes:
  - `generatedAt` (ISO 8601 datetime): timestamp when the response was computed. Enables cache staleness detection and debugging.
  - `filters` (object, where applicable): echo of all applied filter values, including those that were `null`/omitted. Enables client-side verification that the correct filters were applied.
- Applies to: VIZ-UC-01 through VIZ-UC-04.

### VIZ-CN-08 — Query Performance

- Aggregate queries must use Django ORM aggregation functions (`Count`, `Avg`, `Max`, `Min`) computed at the database level, not Python-side iteration over submission objects.
- Queries must use `select_related()` or `prefetch_related()` to avoid N+1 patterns when traversing assignment → assessment or assignment → course relationships.
- Applies to: VIZ-UC-01 through VIZ-UC-04.

### VIZ-CN-09 — Client-Side Chart Rendering

- Backend returns computed aggregate numbers only. Backend does NOT generate chart images, SVG, or HTML.
- Frontend renders charts using:
  - **Recharts** (`^3.7.0`, already installed): bar charts (grade distribution), stat cards (dashboard overview).
  - **Custom CSS grid component**: mood meter quadrant visualization (4-box layout with percentage labels).
- Applies to: all VIZ UCs (response contract).

---

## 6) Endpoint Contract

| Method | Path | Auth | UC |
|--------|------|------|-----|
| GET | `/api/v1/visualizations/dashboard` | IsAuthenticated + IsTeacherOrAbove | VIZ-UC-01 |
| GET | `/api/v1/visualizations/courses/{courseId}/summary` | IsAuthenticated + IsTeacherOrAbove + course ownership gate | VIZ-UC-02 |
| GET | `/api/v1/visualizations/assignments/{assignmentId}/summary` | IsAuthenticated + IsTeacherOrAbove + assignment ownership gate | VIZ-UC-03 |
| GET | `/api/v1/visualizations/assignments/{assignmentId}/mood-meter` | IsAuthenticated + IsTeacherOrAbove + assignment ownership gate + mood meter type gate | VIZ-UC-04 |

> **Trailing-slash note:** Django framework may accept trailing-slash variants. Canonical paths in this contract omit the trailing slash.

**Removed endpoint:**
- `POST /api/v1/visualization/` — legacy raw-data endpoint. Removed entirely; replaced by the aggregate endpoints above. Associated code to remove: `visualizations/views.py::get_visualizations`, `visualizations/serializers.py::VisualizationFilterSerializer`, `core/dtos.py::VisualizationSubmissionDTO`, `visualizations/urls.py` route, `config/urls.py` include path. Raw submission data available through FR-08 SUB endpoints.

**Query parameters (VIZ-UC-02, VIZ-UC-03):**

| Param | Type | Endpoints | Description |
|-------|------|-----------|-------------|
| `startDate` | ISO date string | VIZ-UC-02, VIZ-UC-03 | Filter start (inclusive). VIZ-UC-02: filters by assignment `open_at`. VIZ-UC-03: filters by submission `submitted_at`. |
| `endDate` | ISO date string | VIZ-UC-02, VIZ-UC-03 | Filter end (inclusive). |
| `category` | string | VIZ-UC-02 | Filter assignments by assessment category. |
| `assessmentId` | int | VIZ-UC-02 | Filter assignments by assessment ID. |

---

## 7) Error Model

Standard error payload:
- `{"detail": "<message>"}` for validation, not-found, or authorization errors.

Expected statuses by UC:

| Status | Meaning | Applies To |
|--------|---------|------------|
| `200` | Success — aggregate data returned | All VIZ UCs |
| `400` | Invalid query parameter type or value | VIZ-UC-02, VIZ-UC-03 |
| `401` | Unauthenticated request | All VIZ UCs |
| `403` | Role violation (student) or ownership violation (teacher accessing non-owned course/assignment) | All VIZ UCs |
| `404` | Course or assignment not found | VIZ-UC-02, VIZ-UC-03, VIZ-UC-04 |
| `409` | Incompatible assessment type (non-mood-meter assignment on `/mood-meter` endpoint) | VIZ-UC-04 |

---

## 8) Test Strategy by Layer

### Backend Unit
- Aggregate computation: average, median, high, low, distribution binning.
- Null safety: `avgScore` returns `null` with zero graded submissions.
- Distribution bin edge cases: scores at boundaries (59.5, 89.5, >100, <0).
- Completion rate computation per denominator definition.
- Anonymization field stripping for researcher without `VIEW_IDENTIFIABLE_VIZ`.
- Mood meter quadrant classification from `row`/`col` values.
- Mood meter type gate: 409 for non-mood-meter assignments.

### Backend Integration
- Route + auth + serializer + persistence:
  - `tests/integration/test_visualizations_routes.py`
  - FR-09 traceability tests for all VIZ-CNs.
- Ownership gate tests:
  - Teacher can access own course/assignment, rejected for others.
  - Researcher accesses any course/assignment.
  - Admin accesses any course/assignment.
- Anonymization integration:
  - Researcher without sudo sees no IDs or names.
  - Researcher with `VIEW_IDENTIFIABLE_VIZ` sees full data.
- Query param filtering:
  - Date range filtering on course and assignment endpoints.
  - Category and assessmentId filtering on course endpoint.

### Frontend Unit/Integration
- Recharts chart components render correctly with aggregate data shapes.
- Mood meter custom grid component renders quadrant percentages.
- Stat cards display `null` values gracefully (e.g., "N/A" instead of "0").
- Deferred until frontend implementation phase.

### System Tests (Black Box)
- `ST-VIZ-UC-01` through `ST-VIZ-UC-04`
- Required constraint checks:
  - `ST-VIZ-CN-01` (researcher anonymization with/without sudo)
  - `ST-VIZ-CN-02` (distribution bin correctness)
  - `ST-VIZ-CN-03` (teacher course ownership gate)
  - `ST-VIZ-CN-04` (mood meter type gate, 409)
  - `ST-VIZ-CN-05` (null safety for aggregates)
  - `ST-VIZ-CN-08` (no N+1 queries under load)

---

## 9) NFR Cross-References

- **NFR-Security**
  - Role gate enforced server-side (`IsAuthenticated` + `IsTeacherOrAbove`).
  - Students blocked from all VIZ access (403).
  - Teacher course ownership gate enforced on all endpoints.
  - Researcher anonymization via `VIEW_IDENTIFIABLE_VIZ` sudo permission prevents PII exposure.
  - Mood meter 409 message is generic to prevent assessment type enumeration.
- **NFR-Privacy**
  - Researcher anonymization aligns with data minimization principles: identifiable fields omitted entirely when not authorized.
  - Mood meter responses are inherently aggregate (no student-level data exposed).
- **NFR-Reliability**
  - Read-only endpoints; no mutations.
  - Deterministic status codes and error payloads.
  - Null safety prevents divide-by-zero errors.
- **NFR-Performance**
  - Database-level aggregation (`Count`, `Avg`, etc.) instead of Python-side computation.
  - `select_related` / `prefetch_related` prevents N+1 query patterns.
  - `generatedAt` enables client-side cache staleness detection.
- **NFR-Maintainability**
  - Visualization domain behavior centralized in `visualizations/services.py`.
  - Each endpoint has a dedicated service function with clear aggregate return type.
  - Anonymization applied as a response-level transform, not scattered through service logic.

---

## 10) Cross-Domain References

| FR | Reference | Notes |
|----|-----------|-------|
| FR-03 SUDO | `VIEW_IDENTIFIABLE_VIZ` added to `SudoPermission` enum | New enum value; checked via `has_sudo_permission(user, SudoPermission.VIEW_IDENTIFIABLE_VIZ)`. FR-03 spec must be updated to include this permission in SUDO-CN-09 scope definitions. |
| FR-05 CRS | Course ownership (`CRS-CN-01`) | Teacher ownership gate uses `course.teacher_profile` to restrict VIZ access. |
| FR-06 ASMT | `GradingMode.MOOD_METER` | VIZ-UC-04 mood meter type gate checks assessment grading mode. Assessment metadata (`title`, `category`) used in VIZ response fields. |
| FR-07 ASGN | Assignment → course → teacher relationship | Assignment ownership derived via `assignment.course.teacher_profile` for VIZ-UC-03/04 ownership gate. |
| FR-08 SUB | Submission data source | All VIZ aggregates are computed from `Submission` records. `SubmissionStatus` enum values (`NOT_STARTED`, `IN_PROGRESS`, `SUBMITTED`, `GRADED`) drive completion rate and grade computations. |

---

## 11) Current Implementation Alignment Notes

As of 2026-03-03, FR-09 backend aggregate contract is implemented and verified in integration tests.

Completed alignment:
1. Legacy raw endpoint removed; aggregate GET endpoints live under `/api/v1/visualizations/*`.
2. Legacy serializer/DTO path removed (`VisualizationFilterSerializer`, `VisualizationSubmissionDTO`).
3. Aggregate services use DB-side query/aggregation patterns (`Count`, `Avg`, `Max`, `Min`, `Case`, `Subquery`).
4. `VIEW_IDENTIFIABLE_VIZ` sudo permission is enforced for researcher de-anonymization.
5. Teacher ownership gates are enforced at course and assignment scopes.
6. Researcher anonymization omits identifiable fields (IDs/titles/names) while retaining numeric aggregates.
7. Mood meter type gate returns `409 Conflict` on non-mood-meter assessments.
8. Integration suite covers UC/CN behavior and representative error paths (`tests/integration/test_visualizations_routes.py`).

Known deferred/frontend items:
1. Mood meter frontend visualization UX is deferred for now; backend endpoint and contract remain in place.
2. Additional frontend filtering controls are deferred; backend filtering contract remains available.
