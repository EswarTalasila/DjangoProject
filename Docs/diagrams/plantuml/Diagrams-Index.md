# Diagrams Index

All paths are relative to `Docs/diagrams/plantuml/`.

## UML Class Diagrams (Backend)

- `Docs/diagrams/plantuml/uml/class/backend/backend-accounts.wsd`
- `Docs/diagrams/plantuml/uml/class/backend/backend-assessments.wsd`
- `Docs/diagrams/plantuml/uml/class/backend/backend-assignments.wsd`
- `Docs/diagrams/plantuml/uml/class/backend/backend-courses.wsd`
- `Docs/diagrams/plantuml/uml/class/backend/backend-exports.wsd`
- `Docs/diagrams/plantuml/uml/class/backend/backend-services.wsd`
- `Docs/diagrams/plantuml/uml/class/backend/backend-submissions.wsd`
- `Docs/diagrams/plantuml/uml/class/backend/backend-visualizations.wsd`

## UML Class Diagrams (Frontend)

- (none)

## UML Entity Diagrams (Postgres)

- `Docs/diagrams/plantuml/uml/entity/postgres/postgres-accounts.wsd`
- `Docs/diagrams/plantuml/uml/entity/postgres/postgres-all.wsd`
- `Docs/diagrams/plantuml/uml/entity/postgres/postgres-assessments.wsd`
- `Docs/diagrams/plantuml/uml/entity/postgres/postgres-assignments.wsd`
- `Docs/diagrams/plantuml/uml/entity/postgres/postgres-courses.wsd`
- `Docs/diagrams/plantuml/uml/entity/postgres/postgres-exports.wsd`
- `Docs/diagrams/plantuml/uml/entity/postgres/postgres-submissions.wsd`
- `Docs/diagrams/plantuml/uml/entity/postgres/postgres-visualizations.wsd`

## Sequence Diagrams (API, from OTEL traces)

### assessments

#### success

- `sequence/api/assessments/success/seq-delete-api-v1-assessments-<int-assessment_id>-200.wsd`
- `sequence/api/assessments/success/seq-get-api-v1-assessments-200.wsd`
- `sequence/api/assessments/success/seq-get-api-v1-assessments-<int-assessment_id>-200.wsd`
- `sequence/api/assessments/success/seq-post-api-v1-assessments-201.wsd`
- `sequence/api/assessments/success/seq-post-api-v1-assessments-<int-assessment_id>-teacher-self-assess-201.wsd`
- `sequence/api/assessments/success/seq-put-api-v1-assessments-<int-assessment_id>-200.wsd`

#### error

- `sequence/api/assessments/error/seq-delete-api-v1-assessments-<int-assessment_id>-403.wsd`
- `sequence/api/assessments/error/seq-get-api-v1-assessments-401.wsd`
- `sequence/api/assessments/error/seq-get-api-v1-assessments-<int-assessment_id>-404.wsd`
- `sequence/api/assessments/error/seq-post-api-v1-assessments-<int-assessment_id>-teacher-self-assess-400.wsd`

### assignments

#### success

- `sequence/api/assignments/success/seq-delete-api-v1-assignments-<int-assignment_id>-200.wsd`
- `sequence/api/assignments/success/seq-get-api-v1-assignments-<int-assignment_id>-200.wsd`
- `sequence/api/assignments/success/seq-get-api-v1-assignments-<int-assignment_id>-submissions-200.wsd`
- `sequence/api/assignments/success/seq-get-api-v1-assignments-courses-<int-course_id>-200.wsd`
- `sequence/api/assignments/success/seq-get-api-v1-assignments-users-<int-user_id>-200.wsd`
- `sequence/api/assignments/success/seq-post-api-v1-assignments-201.wsd`
- `sequence/api/assignments/success/seq-post-api-v1-assignments-<int-assignment_id>-submissions-201.wsd`

#### error

- `sequence/api/assignments/error/seq-get-api-v1-assignments-<int-assignment_id>-404.wsd`
- `sequence/api/assignments/error/seq-get-api-v1-assignments-users-<int-user_id>-401.wsd`

### auth

#### success

- `sequence/api/auth/success/seq-delete-api-v1-auth-user-<str-username>-200.wsd`
- `sequence/api/auth/success/seq-get-api-v1-auth-teachers-admins-200.wsd`
- `sequence/api/auth/success/seq-post-api-v1-auth-check-email-200.wsd`
- `sequence/api/auth/success/seq-post-api-v1-auth-create-bulk-200.wsd`
- `sequence/api/auth/success/seq-post-api-v1-auth-createuser-200.wsd`
- `sequence/api/auth/success/seq-post-api-v1-auth-edituser-<int-user_id>-200.wsd`
- `sequence/api/auth/success/seq-post-api-v1-auth-login-200.wsd`
- `sequence/api/auth/success/seq-post-api-v1-auth-register-200.wsd`
- `sequence/api/auth/success/seq-post-api-v1-auth-users-<int-user_id>-set-password-200.wsd`
- `sequence/api/auth/success/seq-put-api-v1-auth-reset-<int-user_id>-200.wsd`

#### error

- `sequence/api/auth/error/seq-get-api-v1-auth-teachers-admins-401.wsd`
- `sequence/api/auth/error/seq-post-api-v1-auth-check-email-404.wsd`
- `sequence/api/auth/error/seq-post-api-v1-auth-create-bulk-400.wsd`
- `sequence/api/auth/error/seq-post-api-v1-auth-createuser-401.wsd`
- `sequence/api/auth/error/seq-post-api-v1-auth-edituser-<int-user_id>-404.wsd`
- `sequence/api/auth/error/seq-post-api-v1-auth-google-400.wsd`
- `sequence/api/auth/error/seq-post-api-v1-auth-login-401.wsd`
- `sequence/api/auth/error/seq-post-api-v1-auth-register-400.wsd`
- `sequence/api/auth/error/seq-post-api-v1-auth-users-<int-user_id>-set-password-400.wsd`
- `sequence/api/auth/error/seq-post-api-v1-auth-users-<int-user_id>-set-password-404.wsd`
- `sequence/api/auth/error/seq-put-api-v1-auth-reset-<int-user_id>-401.wsd`

### courses

#### success

- `sequence/api/courses/success/seq-delete-api-v1-courses-<int-course_id>-204.wsd`
- `sequence/api/courses/success/seq-delete-api-v1-courses-<int-course_id>-students-<int-student_user_id>-200.wsd`
- `sequence/api/courses/success/seq-get-api-v1-courses-200.wsd`
- `sequence/api/courses/success/seq-get-api-v1-courses-<int-course_id>-200.wsd`
- `sequence/api/courses/success/seq-get-api-v1-courses-<int-course_id>-students-200.wsd`
- `sequence/api/courses/success/seq-post-api-v1-courses-200.wsd`
- `sequence/api/courses/success/seq-put-api-v1-courses-<int-course_id>-200.wsd`

#### error

- `sequence/api/courses/error/seq-get-api-v1-courses-401.wsd`
- `sequence/api/courses/error/seq-get-api-v1-courses-<int-course_id>-404.wsd`
- `sequence/api/courses/error/seq-post-api-v1-courses-400.wsd`

### export

#### error

- `sequence/api/export/error/seq-post-api-v1-export-501.wsd`

### students

#### success

- `sequence/api/students/success/seq-get-api-v1-students-<int-student_id>-assignments-<int-assignment_id>-submission-200.wsd`
- `sequence/api/students/success/seq-get-api-v1-students-<int-student_id>-submissions-200.wsd`
- `sequence/api/students/success/seq-post-api-v1-students-200.wsd`
- `sequence/api/students/success/seq-post-api-v1-students-bulk-200.wsd`
- `sequence/api/students/success/seq-put-api-v1-students-<int-student_id>-assignments-<int-assignment_id>-draft-200.wsd`

#### error

- `sequence/api/students/error/seq-post-api-v1-students-400.wsd`
- `sequence/api/students/error/seq-post-api-v1-students-403.wsd`
- `sequence/api/students/error/seq-post-api-v1-students-bulk-400.wsd`

### submissions

#### success

- `sequence/api/submissions/success/seq-get-api-v1-submissions-<int-submission_id>-200.wsd`
- `sequence/api/submissions/success/seq-get-api-v1-submissions-mine-200.wsd`
- `sequence/api/submissions/success/seq-patch-api-v1-submissions-<int-submission_id>-override-score-200.wsd`
- `sequence/api/submissions/success/seq-put-api-v1-submissions-200.wsd`

#### error

- `sequence/api/submissions/error/seq-get-api-v1-submissions-mine-400.wsd`
- `sequence/api/submissions/error/seq-patch-api-v1-submissions-<int-submission_id>-override-score-400.wsd`

### teachers

#### success

- `sequence/api/teachers/success/seq-get-api-v1-teachers-<int-teacher_id>-submissions-200.wsd`

### visualization

#### success

- `sequence/api/visualization/success/seq-post-api-v1-visualization-200.wsd`

#### error

- `sequence/api/visualization/error/seq-post-api-v1-visualization-403.wsd`

