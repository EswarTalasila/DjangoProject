# Frontend to Backend Mapping

## Purpose
Document exactly which Angular services call which API endpoints for parity verification.

## Source inputs
- Frontend services: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-frontend-services.wsd`
- Runtime sequences: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/sequence`
- Controller UML: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-controllers.wsd`

## Mapping (initial placeholders)

### AuthService
- login() -> POST /api/auth/login
- googleLogin() -> POST /api/auth/google
- register() -> POST /api/auth/register
- checkEmail() -> POST /api/auth/check-email

### UserService / AdminService
- createUser() -> POST /api/auth/createuser
- createUsersBulk() -> POST /api/auth/create/bulk
- editUser() -> POST /api/auth/edituser/{id}
- deleteUser() -> DELETE /api/auth/user/{username}
- listTeachersAdmins() -> GET /api/auth/teachers-admins

### CourseService
- createCourse() -> POST /api/courses
- listCourses() -> GET /api/courses
- getCourse() -> GET /api/courses/{id}
- updateCourse() -> PUT /api/courses/{id}
- deleteCourse() -> DELETE /api/courses/{id}
- listCourseStudents() -> GET /api/courses/{id}/students
- removeCourseStudent() -> DELETE /api/courses/{id}/students/{id}

### StudentService
- createStudent() -> POST /api/students
- bulkCreateStudents() -> POST /api/students/bulk
- listStudentSubmissions() -> GET /api/students/{id}/submissions

### AssessmentService
- createAssessment() -> POST /api/assessments
- listAssessments() -> GET /api/assessments
- getAssessment() -> GET /api/assessments/{id}
- updateAssessment() -> PUT /api/assessments/{id}
- deleteAssessment() -> DELETE /api/assessments/{id}
- teacherSelfAssess() -> POST /api/assessments/{id}/teacher-self-assess

### AssignmentService
- createAssignment() -> POST /api/assignments
- getAssignment() -> GET /api/assignments/{id}
- listAssignmentsByCourse() -> GET /api/assignments/courses/{id}
- listAssignmentsByUser() -> GET /api/assignments/users/{id}
- deleteAssignment() -> DELETE /api/assignments/{id}
- createSubmission() -> POST /api/assignments/{id}/submissions

### SubmissionService
- getSubmission() -> GET /api/submissions/{id}
- listByAssignment() -> GET /api/assignments/{id}/submissions
- listByStudent() -> GET /api/students/{id}/submissions
- listByTeacher() -> GET /api/teachers/{id}/submissions
- getByStudentAssignment() -> GET /api/students/{id}/assignments/{id}/submission
- listMine() -> GET /api/submissions/me
- updateSubmission() -> PUT /api/submissions
- overrideScore() -> PATCH /api/submissions/{id}/override-score

### VisualizationService
- getVisualization() -> POST /api/visualization

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
