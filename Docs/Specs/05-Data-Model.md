# Data Model

## Core entities
- User (Admin, Teacher, Student)
- StudentProfile
- Course
- Enrollment
- Assessment
- Question
- Assignment
- Submission
- Answer

## Relationships (target)
- Course has many Enrollments.
- Enrollment links StudentProfile to Course.
- Assessment has many Questions.
- Assignment links Assessment to Course and has date window.
- Submission links Assignment to StudentProfile and stores Answers.

## Required constraints
- Enforce foreign keys for all relationships.
- Use `ON DELETE` rules to prevent orphan data (prefer archive over delete).
- Stable identifiers for questions when submissions exist (versioning).

## Indexing (initial set)
- `assignment_id`, `student_id`, `course_id`, `submitted_at` for submissions.
- `course_id` and `student_id` for enrollments.
- `teacher_id` for courses and assignments.

## Migration guidance
- Replace raw ID fields with foreign keys in ORM models.
- Introduce data migrations to backfill missing relationships.
- Implement archival flags instead of destructive deletes.

## Diagram references
- Entity structure: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-entities.wsd`
- DTO to entity map: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-dto-entity-map.wsd`

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
