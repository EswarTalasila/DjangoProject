# User Stories

## General (All Users)

### US-01 Login with email/password
As a user, I can log in with my registered email and password so I can access my role-specific features.

Acceptance criteria:
- Login accepts email + password and returns a session or access token.
- Invalid credentials return a generic error (no user enumeration).
- Successful login routes the user to their role landing page.

### US-02 Login with Google OAuth
As a user, I can log in with Google if my email is registered, so I can authenticate without a local password.

Acceptance criteria:
- OAuth login is permitted only for registered users.
- A successful OAuth login creates a valid session/access token.
- No user records are created by OAuth alone (admin/teacher create accounts).

### US-03 First-time password setup
As a user, I can set my password the first time I log in after being created or after reset.

Acceptance criteria:
- Password setup requires a time-limited token; no public userId access.
- The token can only be used once.
- Password policy is enforced (length/complexity).

### US-04 Password reset
As a user, I can reset my password when an admin/teacher initiates a reset.

Acceptance criteria:
- Reset triggers a time-limited token and invalidates old sessions.
- The reset flow does not reveal account existence to unauthenticated users.

## Administrator

### US-05 Create teacher/admin accounts
As an admin, I can create teacher/admin accounts individually or in bulk.

Acceptance criteria:
- Admins can set name, email, role, and optionally a temporary password.
- Bulk creation supports CSV upload with validation.
- Created users must set a password on first login.

### US-06 View/edit/delete staff accounts
As an admin, I can view, edit, delete, and reset passwords for teacher/admin accounts.

Acceptance criteria:
- Admins can list staff accounts with filters.
- Role changes are restricted to admin-only.
- Deleting staff accounts does not delete historical data.

### US-07 Create/edit/delete assessments
As an admin, I can create and manage assessments with multiple question types and grading modes.

Acceptance criteria:
- Supports grading modes: auto, manual, hybrid, rubric, reflection, mood meter.
- Editing is restricted when submissions exist (versioning or lock).
- Deleting is restricted when submissions exist (archive vs delete).

### US-08 View/export aggregate data
As an admin, I can view aggregate statistics and export as CSV.

Acceptance criteria:
- Filters for course, teacher, assessment category, and assessment.
- CSV export is consistent with on-screen data.
- Export jobs are bounded and paginated for large datasets.

## Teacher

### US-09 Create/edit/delete courses
As a teacher, I can create and manage my courses.

Acceptance criteria:
- Teachers can rename and delete courses.
- Deleting a course archives related records or requires confirmation.

### US-10 Manage students in courses
As a teacher, I can add/edit/remove students in my courses, individually or via bulk upload.

Acceptance criteria:
- Bulk upload supports CSV templates with validation errors.
- Teachers can reset student passwords.
- Teachers cannot edit students outside their courses.

### US-11 Assign assessments to courses
As a teacher, I can assign assessments to a course with open/close dates.

Acceptance criteria:
- Teachers can select assessment(s), course(s), and date ranges.
- Assignments are visible to students during active windows.

### US-12 View submissions and grade
As a teacher, I can view submissions and apply grading criteria.

Acceptance criteria:
- Teachers can access submissions for their course assignments only.
- Manual grading uses rubric criteria provided by admins.
- Score overrides are audited and persisted.

### US-13 View/export trends
As a teacher, I can view aggregate trends and export PDF reports.

Acceptance criteria:
- Filters: mood meter, course, student, assessment, category.
- PDF export completes for typical data sets and includes charts.

## Student

### US-14 View assignments
As a student, I can view my open assignments and their statuses.

Acceptance criteria:
- Assignment list is filtered to the student’s courses.
- Status reflects not started/in progress/submitted/graded.

### US-15 Complete assignments
As a student, I can complete and submit assignments.

Acceptance criteria:
- Supports multiple choice, short answer, number scale, mood meter.
- Submission is validated and persisted.
- Students cannot submit outside open/close windows.

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
