# Functional Requirements

## FR-01 Authentication and authorization
- Support email/password login and Google OAuth login for pre-registered users.
- Enforce role-based access control for ADMIN, TEACHER, STUDENT.
- Use time-limited tokens for first-login and password reset.
- Disallow public role assignment; only admins create teachers/admins.

## FR-00 API compatibility
- Maintain existing endpoint paths and payload shapes used by the Angular frontend.
- Add versioning using best practice (e.g., `/api/v1`), while providing a compatibility path for existing `/api/*` routes during transition.
- No new endpoints unless required to preserve current UI behavior.

## FR-02 User management (admin/teacher)
- Admin can create, edit, delete teacher/admin accounts, including bulk CSV creation.
- Teacher can create, edit, delete student accounts for their courses only.
- User edits must validate ownership and role rules.

## FR-03 Courses and enrollment
- Teachers can create, edit, delete courses.
- Teachers can enroll students individually or in bulk.
- Enrollment actions must be scoped to the teacher’s courses.

## FR-04 AssignmentTemplates
- Admin can create assignment templates with grading modes:
  - AUTO, MANUAL, HYBRID, RUBRIC, REFLECTION, MOOD_METER.
- Admin can edit assignment templates prior to submissions; after submissions, assignment template is versioned or locked.
- Admin can archive assignment templates without deleting historical data.

## FR-05 Assignments
- Teachers can assign assignment templates to courses with open/close dates.
- Assignment creation does not pre-create all submissions unless required for legacy compatibility.
- Students can view assignments within open/close windows.

## FR-06 Submissions and grading
- Students can create submissions for open assignments.
- Teachers can view and grade submissions for their courses.
- Score overrides must persist and produce audit logs.

## FR-07 Visualization and reporting
- Admin and teacher dashboards provide aggregate views (charts + tables).
- Filtering by course, teacher, student, assignment template, category.
- Teacher self-reflection trends should be available in visualization.

## FR-08 Export
- CSV export for aggregate data (admin).
- PDF export for teacher dashboards and mood meter.
- Export must be bounded/paginated for large data sets.

## FR-09 Image upload (future gap closure)
- If assignment template images are supported in UI, backend must support upload and retrieval.
- Storage may be Postgres (bytea) or filesystem; avoid cloud storage dependency.

## FR-10 Archival and lifecycle
- Replace destructive deletes with archival flags where historical data is needed.
- Archived records must be excluded from default queries but still retrievable by admins.

## FR-11 Proxy-agnostic API
- Backend must operate behind any reverse proxy using standard headers.
- Support `X-Forwarded-Proto`, `X-Forwarded-Host`, and `X-Forwarded-For`.

## FR-12 API compatibility
- Maintain existing frontend routes and API paths where possible to keep UI unchanged.
- Document any unavoidable API changes and provide shims during transition.

## Diagram references
- Current API flow coverage: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/sequence`
- Frontend-to-backend call map: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-frontend-backend-map.wsd`

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
