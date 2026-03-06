# FR-10 Export (EXP) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | EXP |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER |
| **Related Issues** | — |
| **Dependencies** | FR-03 SUDO (`EXPORT_IDENTIFIABLE` permission), FR-05 CRS (course ownership, enrollment data), FR-06 ASMT (assessment metadata, `GradingMode`), FR-07 ASGN (assignment data), FR-08 SUB (submission data source) |

---

## 1) Scope

### In Scope
- Course roster CSV export: enrollment list with student details, consent flag, enrollment status.
- Course submission results CSV export: gradebook data with optional serialized answer details via `includeAnswers=true`.
- Cross-course submission CSV export for researchers and admins with required date-range filters.
- Streaming CSV delivery via Django `StreamingHttpResponse` with `QuerySet.iterator()`.
- Role-gated access: `IsTeacherOrAbove` for course-scoped endpoints; `IsResearcherOrAdmin` for cross-course endpoint. Students excluded.
- Researcher anonymization: identifiable columns omitted unless researcher holds `EXPORT_IDENTIFIABLE` sudo permission and explicitly opts in via `identifiable=true` query param.
- Row caps: 10,000 rows for course-scoped exports; 5,000 rows for cross-course exports.
- Required filter enforcement for cross-course exports (`startDate` + `endDate` mandatory).
- Server-side audit logging for every export request (`ExportAuditLog` model).
- Export metadata HTTP response headers (`X-Export-Generated-At`, `X-Export-Anonymized`, `X-Export-Row-Count`).

### Out of Scope
- PDF export (deferred to future FR-10 extension).
- Mood meter aggregate/trend export (FR-09 VIZ handles aggregates; mood meter submissions are included as regular submission rows when filtered by assignment or category).
- Student-facing exports (students cannot access EXP endpoints).
- Background job / async export processing.
- File storage or download links.
- Assessment template export (FR-06 ASMT domain).
- Cross-course roster export (roster is always course-scoped).
- Server-side chart or visualization generation.
- Wireframes and Playwright E2E scripts (tracked separately).

### Removals
- `POST /api/v1/export/` — current 501 stub endpoint. Replaced entirely by the GET endpoints defined in this spec. Associated code to remove: `exports/views.py::export_stub`, `exports/urls.py` route. URL mount in `config/urls.py` updated from `api/v1/export/` to `api/v1/exports/`.

---

## 2) Actors

| Role | Type | EXP domain permissions |
|------|------|------------------------|
| ADMIN | System role (`is_staff=True`) | Full export access across all courses; identifiable data always visible |
| RESEARCHER | User role | Export access across all courses; identifiable data requires `EXPORT_IDENTIFIABLE` sudo permission + explicit `identifiable=true` query param |
| TEACHER | User role | Export access for own courses only; identifiable data visible for own courses |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER

> **STUDENT excluded:** Students cannot access any EXP endpoint. `IsTeacherOrAbove` / `IsResearcherOrAdmin` permission rejects student requests with `403 Forbidden`.

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| EXP-US-01 | TEACHER | As a teacher I can export a course roster as CSV so that I have an offline list of enrolled students with consent status. |
| EXP-US-02 | TEACHER | As a teacher I can export submission results for a course as CSV so that I can analyze grades in a spreadsheet. |
| EXP-US-03 | TEACHER | As a teacher I can include detailed answer data in submission exports so that I can review individual student responses offline. |
| EXP-US-04 | RESEARCHER | As a researcher I can export anonymized submission data across courses so that I can conduct cross-cohort statistical analysis. |
| EXP-US-05 | RESEARCHER | As a researcher with `EXPORT_IDENTIFIABLE` sudo permission I can export identifiable submission data so that I can conduct detailed research with appropriate authorization. |
| EXP-US-06 | ADMIN | As an admin I can export any course's roster or submissions so that I can audit system-wide data. |

---

## 4) Use Cases

### EXP-UC-01 — Course Roster Export

**Roles:** ADMIN, RESEARCHER, TEACHER
**Endpoint:** `GET /api/v1/exports/courses/{courseId}/roster`
**Query Params:** `status` (string, optional: `ACTIVE`, `DROPPED`; default: all), `identifiable` (boolean, optional; researcher-only, requires `EXPORT_IDENTIFIABLE` sudo)

**Main Flow:**
1. Caller requests roster export for a course.
2. System validates caller has TEACHER or above role via `IsTeacherOrAbove`.
3. System resolves course by `courseId`.
4. System validates caller access:
   - TEACHER: must own the course (`course.teacher_profile == user.teacher_profile`).
   - RESEARCHER / ADMIN: can access any course.
5. System queries enrollments for the course with `select_related('student_profile__user')`.
6. If `status` param provided, filter enrollments by enrollment status.
7. System estimates row count. If count exceeds 10,000 (EXP-CN-03), return `422`.
8. System determines anonymization mode (EXP-CN-01):
   - TEACHER / ADMIN: identifiable.
   - RESEARCHER + `EXPORT_IDENTIFIABLE` sudo + `identifiable=true`: identifiable.
   - RESEARCHER without sudo or without `identifiable=true`: anonymized.
9. System logs audit entry (EXP-CN-06).
10. System streams CSV via `StreamingHttpResponse` with `Content-Disposition: attachment; filename="roster-{courseId}-{YYYY-MM-DD}.csv"`.

**Identifiable CSV Columns:**
```
studentId, studentName, studentUsername, consent, enrollmentStatus, enrolledAt, courseId, courseName
```

**Anonymized CSV Columns (researcher without EXPORT_IDENTIFIABLE):**
```
consent, enrollmentStatus, enrolledAt
```

> **Anonymized roster rationale:** An anonymized roster omits student identity but retains consent rates, enrollment status distribution, and enrollment timing — useful for research on participation patterns without PII exposure.

**Errors:**
- `EXP-UC-01-E1`: Course not found (`404 Not Found`).
- `EXP-UC-01-E2`: Teacher does not own the course (`403 Forbidden`).
- `EXP-UC-01-E3`: Caller is a student (`403 Forbidden` via `IsTeacherOrAbove`).
- `EXP-UC-01-E4`: Unauthenticated request (`401 Unauthorized`).
- `EXP-UC-01-E5`: `identifiable=true` but caller lacks `EXPORT_IDENTIFIABLE` sudo (`403 Forbidden`).
- `EXP-UC-01-E6`: Row count exceeds 10,000 (`422 Unprocessable Entity`).

**Tests (representative):**
- `test_EXP_UC_01_ADMIN`
- `test_EXP_UC_01_RESEARCHER`
- `test_EXP_UC_01_RESEARCHER_anonymized`
- `test_EXP_UC_01_RESEARCHER_identifiable`
- `test_EXP_UC_01_TEACHER`
- `test_EXP_UC_01_TEACHER_filter_by_status`
- `test_EXP_UC_01_E1`
- `test_EXP_UC_01_E2`
- `test_EXP_UC_01_E3`
- `test_EXP_UC_01_E5`
- `test_EXP_CN_01_anonymization`

---

### EXP-UC-02 — Course Submission Export

**Roles:** ADMIN, RESEARCHER, TEACHER
**Endpoint:** `GET /api/v1/exports/courses/{courseId}/submissions`
**Query Params:** `startDate` (ISO date, optional), `endDate` (ISO date, optional), `category` (string, optional), `assessmentId` (int, optional), `assignmentId` (int, optional), `status` (string, optional: `NOT_STARTED`, `IN_PROGRESS`, `SUBMITTED`, `GRADED`), `includeAnswers` (boolean, optional, default `false`), `identifiable` (boolean, optional; researcher-only)

**Main Flow:**
1. Caller requests submission export for a course.
2. System validates caller has TEACHER or above role via `IsTeacherOrAbove`.
3. System resolves course by `courseId`.
4. System validates caller access:
   - TEACHER: must own the course.
   - RESEARCHER / ADMIN: can access any course.
5. System queries submissions linked to assignments in this course with `select_related('assignment__assessment', 'student')`.
6. Apply optional filters:
   - `startDate` / `endDate`: filter by `submitted_at` within range (inclusive).
   - `category`: filter by `assignment.assessment.category`.
   - `assessmentId`: filter by `assignment.assessment.id`.
   - `assignmentId`: filter by `assignment.id`.
   - `status`: filter by submission status.
7. System estimates row count. If count exceeds 10,000 (EXP-CN-03), return `422`.
8. If `includeAnswers=true`, prefetch answers with `prefetch_related('answers')` and type-specific extensions.
9. System determines anonymization mode (EXP-CN-01).
10. System logs audit entry (EXP-CN-06).
11. System streams CSV with `Content-Disposition: attachment; filename="submissions-course-{courseId}-{YYYY-MM-DD}.csv"`.

**Identifiable CSV Columns:**
```
studentId, studentName, studentUsername, consent, assignmentId, assessmentTitle, assessmentCategory, gradingMode, status, score, submittedAt
```

With `includeAnswers=true`, append column:
```
answers
```
(JSON string: array of `{"questionPrompt": "...", "answerType": "...", "value": {...}, "score": ..., "skipped": bool}`)

**Anonymized CSV Columns (researcher without EXPORT_IDENTIFIABLE):**
```
consent, assessmentCategory, gradingMode, status, score, submittedAt
```

With `includeAnswers=true`, append column:
```
answers
```
(JSON string: `questionPrompt` omitted from each answer object to prevent assessment identification)

**Errors:**
- `EXP-UC-02-E1`: Course not found (`404 Not Found`).
- `EXP-UC-02-E2`: Teacher does not own the course (`403 Forbidden`).
- `EXP-UC-02-E3`: Caller is a student (`403 Forbidden` via `IsTeacherOrAbove`).
- `EXP-UC-02-E4`: Unauthenticated request (`401 Unauthorized`).
- `EXP-UC-02-E5`: Invalid query param type (`400 Bad Request`).
- `EXP-UC-02-E6`: `identifiable=true` but caller lacks `EXPORT_IDENTIFIABLE` sudo (`403 Forbidden`).
- `EXP-UC-02-E7`: Row count exceeds 10,000 (`422 Unprocessable Entity`; response: `{"detail": "Export too large. Apply filters to reduce dataset."}`).

**Tests (representative):**
- `test_EXP_UC_02_ADMIN`
- `test_EXP_UC_02_RESEARCHER`
- `test_EXP_UC_02_RESEARCHER_anonymized`
- `test_EXP_UC_02_RESEARCHER_identifiable`
- `test_EXP_UC_02_TEACHER`
- `test_EXP_UC_02_TEACHER_filter_by_category`
- `test_EXP_UC_02_TEACHER_filter_by_date_range`
- `test_EXP_UC_02_TEACHER_include_answers`
- `test_EXP_UC_02_E1`
- `test_EXP_UC_02_E2`
- `test_EXP_UC_02_E5`
- `test_EXP_UC_02_E6`

---

### EXP-UC-03 — Cross-Course Submission Export

**Roles:** ADMIN, RESEARCHER
**Endpoint:** `GET /api/v1/exports/submissions`
**Query Params:** `startDate` (ISO date, **required**), `endDate` (ISO date, **required**), `category` (string, optional), `assessmentId` (int, optional), `status` (string, optional), `includeAnswers` (boolean, optional, default `false`), `identifiable` (boolean, optional, default `false`; requires `EXPORT_IDENTIFIABLE` sudo)

**Main Flow:**
1. Caller requests cross-course submission export.
2. System validates caller has RESEARCHER or ADMIN role via `IsResearcherOrAdmin`. Teachers receive `403`.
3. System validates required filters: `startDate` AND `endDate` must both be present. If either is missing, return `400`.
4. System queries all submissions with `select_related('assignment__assessment', 'assignment__course', 'student')`.
5. Filter by `submitted_at` within `[startDate, endDate]` range (inclusive).
6. Apply optional filters: `category`, `assessmentId`, `status`.
7. System estimates row count. If count exceeds 5,000 (EXP-CN-04), return `422`.
8. If `includeAnswers=true`, prefetch answers.
9. System determines anonymization mode (EXP-CN-01):
   - ADMIN: identifiable.
   - RESEARCHER + `EXPORT_IDENTIFIABLE` sudo + `identifiable=true`: identifiable.
   - RESEARCHER without sudo or without `identifiable=true`: anonymized.
10. System logs audit entry (EXP-CN-06).
11. System streams CSV with `Content-Disposition: attachment; filename="submissions-cross-course-{YYYY-MM-DD}.csv"`.

**Identifiable CSV Columns:**
```
courseId, courseName, studentId, studentName, studentUsername, consent, assignmentId, assessmentTitle, assessmentCategory, gradingMode, status, score, submittedAt
```

With `includeAnswers=true`, append `answers` column (same format as EXP-UC-02).

**Anonymized CSV Columns:**
```
consent, assessmentCategory, gradingMode, status, score, submittedAt
```

With `includeAnswers=true`, append `answers` column (`questionPrompt` omitted).

**Errors:**
- `EXP-UC-03-E1`: Caller is not RESEARCHER or ADMIN (`403 Forbidden` via `IsResearcherOrAdmin`).
- `EXP-UC-03-E2`: Missing required filter: `startDate` or `endDate` (`400 Bad Request`; response: `{"detail": "Cross-course export requires startDate and endDate filters"}`).
- `EXP-UC-03-E3`: Unauthenticated request (`401 Unauthorized`).
- `EXP-UC-03-E4`: Invalid query param type (`400 Bad Request`).
- `EXP-UC-03-E5`: `identifiable=true` but caller lacks `EXPORT_IDENTIFIABLE` sudo (`403 Forbidden`).
- `EXP-UC-03-E6`: Row count exceeds 5,000 (`422 Unprocessable Entity`; response: `{"detail": "Export too large. Narrow date range or apply additional filters."}`).

**Tests (representative):** _(EXP-UC-03 cross-course export endpoint removed; see `test_EXP_UC_03_removed_endpoint_returns_404`)_

---

## 5) Constraints

### EXP-CN-01 — Researcher Anonymization via EXPORT_IDENTIFIABLE Sudo

- Researchers without `EXPORT_IDENTIFIABLE` sudo permission receive anonymized CSV exports where identifiable columns are **omitted from the CSV header and data rows** (not nulled, not replaced with placeholder values).
- Researchers WITH `EXPORT_IDENTIFIABLE` sudo receive anonymized exports by default and must explicitly opt in via `identifiable=true` query param to receive identifiable data.
- Identifiable columns subject to omission: `studentId`, `studentName`, `studentUsername`, `courseId`, `courseName`, `assignmentId`, `assessmentTitle`, `questionPrompt` (in answers JSON).
- Non-identifiable columns always retained: `consent`, `assessmentCategory`, `gradingMode`, `status`, `score`, `submittedAt`, `enrollmentStatus`, `enrolledAt`.
- Anonymized answers JSON (when `includeAnswers=true`): omits `questionPrompt` from each answer object. Retains `answerType`, `value`, `score`, `skipped`.
- Authorization check: `has_sudo_permission(user, SudoPermission.EXPORT_IDENTIFIABLE)` from FR-03.
- Requesting `identifiable=true` without `EXPORT_IDENTIFIABLE` sudo returns `403 Forbidden` (not a silent fallback to anonymized).
- Access matrix:
  - TEACHER: identifiable data for own courses only (course ownership gate, not sudo). `identifiable` param ignored.
  - ADMIN: identifiable data everywhere (admin bypasses sudo check). `identifiable` param ignored.
  - RESEARCHER + `EXPORT_IDENTIFIABLE` + `identifiable=true`: identifiable data everywhere.
  - RESEARCHER + `EXPORT_IDENTIFIABLE` + `identifiable` omitted or `false`: anonymized data.
  - RESEARCHER without `EXPORT_IDENTIFIABLE`: anonymized data. `identifiable=true` returns 403.
- Applies to: EXP-UC-01 through EXP-UC-03.

### EXP-CN-02 — Teacher Course Ownership Gate

- Teachers can only export data for courses they own. Cross-teacher data access is prohibited.
- Ownership check: `course.teacher_profile == user.teacher_profile` (from FR-05 `CRS-CN-01`).
- RESEARCHER and ADMIN bypass this check entirely.
- Teachers cannot access the cross-course endpoint (EXP-UC-03); it requires `IsResearcherOrAdmin`.
- Applies to: EXP-UC-01, EXP-UC-02.

### EXP-CN-03 — Course-Scoped Row Cap

- Course-scoped export endpoints (EXP-UC-01, EXP-UC-02) have a maximum row limit of 10,000 records.
- System performs a `COUNT(*)` query before streaming. If count exceeds 10,000, return `422 Unprocessable Entity` with `{"detail": "Export too large. Apply filters to reduce dataset."}`.
- The count query uses the same filters as the export query (status, date range, category, etc.).
- Applies to: EXP-UC-01, EXP-UC-02.

### EXP-CN-04 — Cross-Course Row Cap and Required Filters

- Cross-course export (EXP-UC-03) has a maximum row limit of 5,000 records.
- `startDate` AND `endDate` query params are **required**. Missing either returns `400 Bad Request` with `{"detail": "Cross-course export requires startDate and endDate filters"}`.
- System performs a `COUNT(*)` query before streaming. If count exceeds 5,000, return `422 Unprocessable Entity` with `{"detail": "Export too large. Narrow date range or apply additional filters."}`.
- Additional optional filters (`category`, `assessmentId`, `status`) further narrow the result set.
- Applies to: EXP-UC-03.

### EXP-CN-05 — Streaming CSV Delivery

- All export endpoints use Django `StreamingHttpResponse` with a Python generator.
- The generator uses `QuerySet.iterator(chunk_size=2000)` to avoid loading the full result set into memory.
- CSV rows are written via `csv.writer` wrapping an in-memory pseudo-buffer (single-row buffer pattern).
- The first yielded chunk is the UTF-8 BOM + CSV header row (column names).
- Response includes `Content-Disposition: attachment; filename="{type}-{scope}-{date}.csv"` header.
- Response includes metadata headers:
  - `X-Export-Generated-At`: ISO 8601 datetime when export was initiated.
  - `X-Export-Anonymized`: `true` or `false`.
  - `X-Export-Row-Count`: row count from the pre-stream count query.
- Applies to: EXP-UC-01 through EXP-UC-03.

### EXP-CN-06 — Export Audit Logging

- Every export request generates a server-side audit log entry, regardless of whether the export succeeds or is rejected by a cap/filter check.
- Audit entry fields:
  - `user` (FK → User): actor performing the export.
  - `export_type` (string): `roster` or `submissions`.
  - `scope_course` (FK → Course, nullable): course ID for course-scoped exports; `null` for cross-course.
  - `filters` (JSONField): all applied filter values including those that were null/omitted.
  - `identifiable` (boolean): whether identifiable data was included in the response.
  - `row_count` (int): estimated row count from the count query.
  - `created_at` (DateTimeField, auto_now_add): timestamp.
- Audit entries are stored in the `export_audit_logs` database table (new `ExportAuditLog` model in exports app).
- Audit entry is written BEFORE streaming begins (captures intent, not just completion).
- Applies to: EXP-UC-01 through EXP-UC-03.

### EXP-CN-07 — CSV Format Rules

- CSV uses UTF-8 encoding with BOM (`\xef\xbb\xbf`) for Excel compatibility.
- Fields containing commas, quotes, or newlines are properly escaped per RFC 4180.
- `null` database values are represented as empty strings in CSV cells.
- Date fields use ISO 8601 format (`YYYY-MM-DDTHH:MM:SSZ`).
- Boolean fields use `true`/`false` strings.
- `answers` column (when present) contains a JSON string (single field, properly CSV-escaped).
- Applies to: EXP-UC-01 through EXP-UC-03.

### EXP-CN-08 — Consent Column Semantics

- All exports include a `consent` column reflecting `StudentProfile.consent` value.
- All students are included in exports regardless of consent value — no filtering by consent.
- The consent column is informational: it flags whether the student has given consent, enabling the exporter to make downstream decisions about data handling (FERPA/IRB compliance).
- Applies to: EXP-UC-01 through EXP-UC-03.

### EXP-CN-09 — Query Performance

- Export queries must use `select_related()` to prefetch related models and avoid N+1 patterns:
  - Roster: `select_related('student_profile__user')`.
  - Submissions: `select_related('assignment__assessment', 'assignment__course', 'student')`.
  - Answers (when `includeAnswers=true`): `prefetch_related('answers')` with type-specific extensions.
- Count queries must use the same filter conditions as the data query to ensure consistency between cap check and actual export.
- `QuerySet.iterator(chunk_size=2000)` is required for streaming to limit memory usage.
- Applies to: EXP-UC-01 through EXP-UC-03.

---

## 6) Endpoint Contract

| Method | Path | Auth | UC |
|--------|------|------|-----|
| GET | `/api/v1/exports/courses/{courseId}/roster` | IsAuthenticated + IsTeacherOrAbove + course ownership gate | EXP-UC-01 |
| GET | `/api/v1/exports/courses/{courseId}/submissions` | IsAuthenticated + IsTeacherOrAbove + course ownership gate | EXP-UC-02 |
| GET | `/api/v1/exports/submissions` | IsAuthenticated + IsResearcherOrAdmin | EXP-UC-03 |

> **Trailing-slash note:** Django framework may accept trailing-slash variants. Canonical paths in this contract omit the trailing slash.

**Removed endpoint:**
- `POST /api/v1/export/` — legacy 501 stub. Removed entirely; replaced by the GET endpoints above. Associated code to remove: `exports/views.py::export_stub`, `exports/urls.py` route. URL mount in `config/urls.py` updated from `api/v1/export/` to `api/v1/exports/`.

**Query parameters:**

| Param | Type | Endpoints | Required | Description |
|-------|------|-----------|----------|-------------|
| `status` | string | EXP-UC-01 | No | Filter enrollments: `ACTIVE`, `DROPPED`. Default: all. |
| `startDate` | ISO date | EXP-UC-02, EXP-UC-03 | UC-03: Yes | Filter start (inclusive). Filters by `submitted_at`. |
| `endDate` | ISO date | EXP-UC-02, EXP-UC-03 | UC-03: Yes | Filter end (inclusive). Filters by `submitted_at`. |
| `category` | string | EXP-UC-02, EXP-UC-03 | No | Filter by assessment category. |
| `assessmentId` | int | EXP-UC-02, EXP-UC-03 | No | Filter by assessment ID. |
| `assignmentId` | int | EXP-UC-02 | No | Filter by assignment ID. |
| `status` | string | EXP-UC-02, EXP-UC-03 | No | Filter by submission status: `NOT_STARTED`, `IN_PROGRESS`, `SUBMITTED`, `GRADED`. |
| `includeAnswers` | boolean | EXP-UC-02, EXP-UC-03 | No | Include serialized answer data as JSON column. Default: `false`. |
| `identifiable` | boolean | All | No | Researcher opt-in for identifiable data. Requires `EXPORT_IDENTIFIABLE` sudo. Ignored for TEACHER/ADMIN. Default: `false`. |

> **`status` param disambiguation:** On EXP-UC-01 (roster), `status` refers to enrollment status (`ACTIVE`/`DROPPED`). On EXP-UC-02/03 (submissions), `status` refers to submission status (`NOT_STARTED`/`IN_PROGRESS`/`SUBMITTED`/`GRADED`). The param name is the same; semantics are determined by the endpoint.

---

## 7) Error Model

Standard error payload:
- `{"detail": "<message>"}` for validation, not-found, or authorization errors.

Expected statuses by UC:

| Status | Meaning | Applies To |
|--------|---------|------------|
| `200` | Success — streaming CSV response | All EXP UCs |
| `400` | Missing required filter (cross-course) or invalid query param type/value | EXP-UC-02, EXP-UC-03 |
| `401` | Unauthenticated request | All EXP UCs |
| `403` | Role violation (student), ownership violation (teacher non-owned course), or `identifiable=true` without `EXPORT_IDENTIFIABLE` sudo | All EXP UCs |
| `404` | Course not found | EXP-UC-01, EXP-UC-02 |
| `422` | Result set exceeds row cap — apply filters to reduce dataset | All EXP UCs |

---

## 8) Test Strategy by Layer

### Backend Unit
- CSV generation: verify header row, data rows, proper escaping, UTF-8 BOM.
- Anonymization: identifiable columns omitted for researcher without sudo.
- Anonymized answers JSON: `questionPrompt` stripped.
- Row cap enforcement: 422 returned when count exceeds limit.
- Cross-course required filter: 400 when `startDate`/`endDate` missing.
- Consent column: present for all students regardless of consent value.
- Null safety: null scores and null `submitted_at` represented as empty strings.
- Filter application: date range, category, assessmentId, assignmentId, status filters.
- `identifiable=true` without sudo: 403 returned.

### Backend Integration
- Route + auth + streaming + persistence:
  - `tests/integration/test_exports_routes.py`
  - FR-10 traceability tests for all EXP-CNs.
- Ownership gate tests:
  - Teacher can export own course, rejected for others.
  - Researcher exports any course (anonymized by default).
  - Admin exports any course (identifiable).
- Audit log tests:
  - Every export creates an `ExportAuditLog` entry.
  - Audit entry captures correct user, type, scope, filters, identifiable flag, row count.
- Streaming tests:
  - Response is `StreamingHttpResponse`.
  - `Content-Disposition` header is set with correct filename.
  - Metadata headers (`X-Export-Generated-At`, `X-Export-Anonymized`, `X-Export-Row-Count`) present.
- Cross-course permission tests:
  - Teacher receives 403 on cross-course endpoint.
  - Researcher receives 400 without date range.

### Frontend Unit/Integration
- Export button/link components trigger correct endpoint with appropriate query params.
- Filter UI for date range, category selection.
- Deferred until frontend implementation phase.

### System Tests (Black Box)
- `ST-EXP-UC-01` through `ST-EXP-UC-03`
- Required constraint checks:
  - `ST-EXP-CN-01` (researcher anonymization with/without sudo)
  - `ST-EXP-CN-02` (teacher course ownership gate)
  - `ST-EXP-CN-03` (course-scoped row cap, 422)
  - `ST-EXP-CN-04` (cross-course required filters 400; row cap 422)
  - `ST-EXP-CN-06` (audit log entry created for every export)
  - `ST-EXP-CN-08` (consent column present for all students)

---

## 9) NFR Cross-References

- **NFR-Security**
  - Role gate enforced server-side (`IsAuthenticated` + `IsTeacherOrAbove` / `IsResearcherOrAdmin`).
  - Students blocked from all EXP access (403).
  - Teacher course ownership gate enforced on course-scoped endpoints.
  - Researcher anonymization via `EXPORT_IDENTIFIABLE` sudo prevents PII exposure in exports.
  - `identifiable=true` without sudo returns 403 (explicit rejection, not silent fallback).
  - Audit logging captures every export request for compliance monitoring.
- **NFR-Privacy**
  - Researcher anonymization aligns with data minimization: identifiable columns omitted entirely when not authorized.
  - Consent column included for all students, enabling downstream FERPA/IRB compliance decisions by the exporter.
  - Anonymized answers strip `questionPrompt` to prevent indirect assessment identification.
  - `EXPORT_IDENTIFIABLE` is separate from `VIEW_IDENTIFIABLE_VIZ` — viewing PII in dashboards and exporting PII are different risk levels with independent authorization.
- **NFR-Performance**
  - Streaming CSV via `StreamingHttpResponse` with `iterator(chunk_size=2000)` prevents memory exhaustion.
  - Row caps (10k course-scoped, 5k cross-course) prevent unbounded queries.
  - `select_related` / `prefetch_related` prevents N+1 query patterns.
  - Count query before streaming enables early rejection of oversized exports.
- **NFR-Reliability**
  - Read-only endpoints; no mutations (except audit log writes).
  - Deterministic status codes and error payloads.
  - UTF-8 BOM ensures CSV opens correctly in Excel across platforms.
- **NFR-Maintainability**
  - Export domain behavior centralized in `exports/services.py`.
  - Each endpoint has a dedicated service function with clear return type.
  - Anonymization applied as a column-set transform at the CSV generation layer, not scattered through query logic.

---

## 10) Cross-Domain References

| FR | Reference | Notes |
|----|-----------|-------|
| FR-03 SUDO | `EXPORT_IDENTIFIABLE` added to `SudoPermission` enum | New enum value; checked via `has_sudo_permission(user, SudoPermission.EXPORT_IDENTIFIABLE)`. Separate from `VIEW_IDENTIFIABLE_VIZ` — independent authorization for export PII vs. dashboard PII. |
| FR-05 CRS | Course ownership (`CRS-CN-01`), enrollment data | Teacher ownership gate uses `course.teacher_profile` to restrict EXP access. `Enrollment` model and `EnrollmentStatus` enum are the data source for roster export. |
| FR-06 ASMT | Assessment metadata (`title`, `category`, `GradingMode`) | Assessment fields used in submission CSV columns. `GradingMode` column enables export recipients to identify mood meter vs. graded submissions. |
| FR-07 ASGN | Assignment data | `Assignment.id`, assignment → course → teacher relationship used for submission queries and ownership gate derivation. |
| FR-08 SUB | Submission data source | All submission export data comes from `Submission` records. `SubmissionStatus` enum values drive status column and filter. Answer data serialized via `answer_to_dto` pattern from submissions services. |
| FR-09 VIZ | Visualization aggregates | FR-09 provides dashboard aggregates; FR-10 provides raw data export. No overlap — FR-10 exports row-level data, FR-09 returns computed summaries. Mood meter submissions included in FR-10 as regular rows (no dedicated trend export). |

---

## 11) Current Implementation Alignment Notes

Backend implementation is complete as of 2026-03-03. All items below are resolved unless marked deferred.

1. **Endpoint architecture — DONE.** `POST /api/v1/export/` stub removed. Three GET endpoints implemented: `exports/views.py` (`course_roster`, `course_submissions`, `cross_course_submissions`). URL mount updated to `api/v1/exports/` in `config/urls.py`.
2. **Stub code removed — DONE.** `export_stub` view and old URL route deleted.
3. **Streaming CSV service layer — DONE.** `exports/services.py` implements `export_roster`, `export_course_submissions`, `export_cross_course_submissions` using `StreamingHttpResponse` + `csv.writer` + `QuerySet.iterator(chunk_size=2000)`. Answer serialization uses a local `_serialize_answers` function that mirrors `answer_to_dto` semantics with JSON output and `questionPrompt` omission for anonymized mode.
4. **`EXPORT_IDENTIFIABLE` sudo enum — DONE.** Already existed in `accounts/models.py::SudoPermission`. No change needed.
5. **`ExportAuditLog` model — DONE.** `exports/models.py` with migration `0001_export_audit_log`. Fields: `user`, `export_type`, `scope_course`, `filters`, `identifiable`, `row_count`, `created_at`. Table: `export_audit_logs`.
6. **Teacher course ownership gate — DONE.** `_check_course_access` in `exports/views.py`. TEACHER must own; RESEARCHER/ADMIN bypass.
7. **Anonymization column transform — DONE.** `resolve_anonymization` in `exports/services.py`. Column sets selected at CSV generation layer. Omission (not nulling) of identifiable columns for anonymized exports.
8. **Row cap + filter enforcement — DONE.** Count query before streaming in views. 422 for oversized (10k course-scoped, 5k cross-course). 400 for missing required `startDate`/`endDate` on cross-course.
9. **Tests — DONE.** `tests/integration/test_exports_routes.py` — 39 tests covering all 3 UCs, error paths (E1–E6), CN-01 anonymization, CN-02 ownership, CN-05 streaming headers, CN-06 audit logs, CN-07 UTF-8 BOM, CN-08 consent column, `includeAnswers` identifiable vs. anonymized.
10. **Frontend — DEFERRED.** Export buttons, filter UI, and download UX deferred to frontend implementation phase per project direction.
