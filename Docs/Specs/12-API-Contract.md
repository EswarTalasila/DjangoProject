# API Contract (Draft)

## Purpose
Define exact endpoint paths, methods, request bodies, and response shapes for parity with the current Angular frontend. This is the authoritative contract for the rewrite.

## Scope
- Current runtime endpoints under `/api/v1/*`.
- The assignment template section below reflects the active backend/frontend contract after the hard cutover.

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

## AssignmentTemplates
| Method | Path | Request | Response | Auth | Notes |
|---|---|---|---|---|---|
| POST | /api/v1/assignment-templates | AssignmentTemplateDto | AssignmentTemplateDto | Researcher/Admin | Create |
| GET | /api/v1/assignment-templates | {} | [AssignmentTemplateDto] | Teacher+ | List available templates |
| GET | /api/v1/assignment-templates/{id} | {} | AssignmentTemplateDto | Teacher+ | Detail |
| PATCH | /api/v1/assignment-templates/{id} | AssignmentTemplateDto | AssignmentTemplateDto | Researcher/Admin | Update when unreferenced |
| DELETE | /api/v1/assignment-templates/{id} | {} | 204 No Content | Researcher/Admin | Hard delete when unreferenced |
| POST | /api/v1/assignment-templates/{id}/archive | {} | AssignmentTemplateDto | Researcher/Admin | Archive |
| POST | /api/v1/assignment-templates/{id}/restore | {} | AssignmentTemplateDto | Researcher/Admin | Restore archived template |
| POST | /api/v1/assignment-templates/{id}/publish | {} | AssignmentTemplateDto | Researcher/Admin | Publish draft template |
| POST | /api/v1/assignment-templates/{id}/questions/{questionId}/image | multipart/form-data | QuestionImageDto | Researcher/Admin | Upload question image |
| DELETE | /api/v1/assignment-templates/{id}/questions/{questionId}/image | {} | 204 No Content | Researcher/Admin | Remove question image |

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
| GET | /api/submissions/me | {} | [SubmissionDto] | Student | |
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
