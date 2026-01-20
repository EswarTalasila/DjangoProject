# API Contract (Draft)

## Purpose
Define exact endpoint paths, methods, request bodies, and response shapes for parity with the current Angular frontend. This is the authoritative contract for the rewrite.

## Scope
- All endpoints under `/api/*` used by the current Angular services.
- Versioned aliases under `/api/v1/*` must produce identical payloads.

## Sources of truth
- Controller UML: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-controllers.wsd`
- Runtime sequences: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/sequence`
- Frontend services: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-frontend-services.wsd`

## Auth
| Method | Path | Request | Response | Auth | Notes |
|---|---|---|---|---|---|
| POST | /api/auth/login | {username, password} | {accessToken, id, role, name?} | None | Match current payload exactly |
| POST | /api/auth/register | {name, username, password, role} | string | None | Lock to STUDENT on rewrite |
| POST | /api/auth/google | {accessToken} | {accessToken, id, role, name?} | None | OAuth for registered users |
| POST | /api/auth/check-email | {email} | {exists?, userId?} | None | Replace with non-enumerating response |
| POST | /api/auth/createuser | {...} | {...} | Admin/Teacher | Verify role restrictions |
| POST | /api/auth/create/bulk | [users] | {created, errors} | Admin | Match current behavior |
| POST | /api/auth/edituser/{id} | {...} | {...} | Admin/Teacher | Ownership checks |
| PUT | /api/auth/reset/{id} | {} | {status} | Admin | Reset token flow |
| POST | /api/auth/users/{id}/set-password | text/plain | {status} | Token | First-login token |
| GET | /api/auth/teachers-admins | {} | [users] | Admin | List staff |
| DELETE | /api/auth/user/{username} | {} | {status} | Admin | Delete user |

## Courses
| Method | Path | Request | Response | Auth | Notes |
|---|---|---|---|---|---|
| POST | /api/courses | {name} | CourseDto | Teacher | Ownership enforced |
| GET | /api/courses | {} | [CourseDto] | Teacher/Admin | Scope by role |
| GET | /api/courses/{id} | {} | CourseDto | Teacher/Admin | Ownership enforced |
| PUT | /api/courses/{id} | {name} | CourseDto | Teacher | Ownership enforced |
| DELETE | /api/courses/{id} | {} | {status} | Teacher/Admin | Archive vs delete |
| GET | /api/courses/{id}/students | {} | [StudentDto] | Teacher | Scope to course |
| DELETE | /api/courses/{id}/students/{id} | {} | {status} | Teacher | Remove enrollment |

## Students
| Method | Path | Request | Response | Auth | Notes |
|---|---|---|---|---|---|
| POST | /api/students | StudentDto | StudentDto | Teacher | Create student |
| POST | /api/students/bulk | [StudentDto] | {created, errors} | Teacher | Bulk add |
| GET | /api/students/{id}/submissions | {} | [SubmissionDto] | Teacher | Scope by course |

## Assessments
| Method | Path | Request | Response | Auth | Notes |
|---|---|---|---|---|---|
| POST | /api/assessments | AssessmentDto | AssessmentDto | Admin | Create |
| GET | /api/assessments | {} | [AssessmentDto] | Admin/Teacher | Scope by role |
| GET | /api/assessments/{id} | {} | AssessmentDto | Admin/Teacher | |
| PUT | /api/assessments/{id} | AssessmentDto | AssessmentDto | Admin | Version or lock |
| DELETE | /api/assessments/{id} | {} | {status} | Admin | Archive vs delete |
| POST | /api/assessments/{id}/teacher-self-assess | [AnswerDto] | {status} | Teacher | Reflection flow |

## Assignments
| Method | Path | Request | Response | Auth | Notes |
|---|---|---|---|---|---|
| POST | /api/assignments | AssignmentDto | AssignmentDto | Teacher | |
| GET | /api/assignments/{id} | {} | AssignmentDto | Teacher/Student | Scope by role |
| GET | /api/assignments/courses/{id} | {} | [AssignmentDto] | Teacher | |
| GET | /api/assignments/users/{id} | {} | [AssignmentDto] | Teacher | |
| DELETE | /api/assignments/{id} | {} | {status} | Teacher | Archive vs delete |
| POST | /api/assignments/{id}/submissions | SubmissionDto | SubmissionDto | Teacher/Student | Student submit |

## Submissions
| Method | Path | Request | Response | Auth | Notes |
|---|---|---|---|---|---|
| GET | /api/submissions/{id} | {} | SubmissionDto | Teacher | |
| GET | /api/assignments/{id}/submissions | {} | [SubmissionDto] | Teacher | |
| GET | /api/students/{id}/submissions | {} | [SubmissionDto] | Teacher | |
| GET | /api/teachers/{id}/submissions | {} | [SubmissionDto] | Teacher | |
| GET | /api/students/{id}/assignments/{id}/submission | {} | SubmissionDto | Teacher/Student | |
| GET | /api/submissions/mine | {} | [SubmissionDto] | Student | |
| PUT | /api/submissions | SubmissionDto | SubmissionDto | Teacher | Update grading |
| PATCH | /api/submissions/{id}/override-score | [number] | SubmissionDto | Teacher/Admin | Persist override |

## Visualization
| Method | Path | Request | Response | Auth | Notes |
|---|---|---|---|---|---|
| POST | /api/visualization | FiltersDto | VisualizationDto | Teacher/Admin | Must be paginated |

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
