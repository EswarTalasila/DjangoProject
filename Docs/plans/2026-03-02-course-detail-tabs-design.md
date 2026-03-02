# Course Detail Tabs + Sidebar Cleanup — Design

**Date:** 2026-03-02
**Branch:** feat/fr-implementation
**Status:** Approved

## Goals

1. Restructure the course detail page (`/dashboard/courses/[id]`) into a tabbed layout: Roster, Registration, Assignments, Gradebook.
2. Remove Self Assessment from the teacher sidebar.
3. Implement Roster tab (fully functional) and Registration tab (functional). Assignments and Gradebook are stubs for now.

## Sidebar Changes

Remove the **Self Assessment** item from the teacher's Assessments nav group. Keep Assessment List.

Final teacher sidebar:

| Group                  | Items                            |
|------------------------|----------------------------------|
| Overview               | Dashboard                        |
| Courses                | My Courses, Registration Codes   |
| Assessments            | Assessment List                  |
| Assignments & Grading  | Create Assignment, Gradebook     |

Global Create Assignment and Gradebook remain for cross-course access. When opened from a course tab in the future, they should prefill `courseId`.

## Course Detail Page Tabs

URL-driven via `?tab=roster|registration|assignments|gradebook`, defaulting to `roster`. Back/refresh preserves tab state. Tabs are **lazy-loaded** — each tab fetches its own data only when activated.

### Tab 1 — Roster (functional)

Existing student table moved into a `CourseRosterTab` component.

- Columns: Name, Username, Enrolled, Actions
- Actions per row:
  - **Issue Reset** — calls `issuePasswordResetCode(studentId)`, shows `ResetCodeDialog`
  - **Remove** — existing AlertDialog confirmation, calls `removeStudentFromCourse()`
- Empty state: "No students enrolled in this course."

### Tab 2 — Registration (functional)

`CourseRegistrationTab` component.

- **Generate Code** button → `POST /api/v1/codes` with `{ codeType: "STUDENT", courseId, maxUses: 1 }`
- Table of active (unexpired) student codes for this course
- Backend gap: `GET /api/v1/codes` does not support `?courseId=` filtering. Two options:
  - A) Add `courseId` query param to backend `_list_codes()` (preferred, small change)
  - B) Client-side filter: fetch teacher's active STUDENT codes, filter by `code.courseId === courseId`
- Decision: use client-side filtering for now to avoid backend changes; backend filter can be added later.

### Tab 3 — Assignments (stub)

Placeholder: "Assignments for this course will appear here."

Backend `GET /api/v1/assignments/courses/{courseId}` already exists for future wiring. Will eventually include in-tab Create Assignment button prefilled with this course.

### Tab 4 — Gradebook (stub)

Placeholder: "Gradebook for this course will appear here."

## Component Structure

```
CourseDetailView.tsx          — header, tab bar, tab routing
├── CourseRosterTab.tsx       — student table + Issue Reset + Remove
├── CourseRegistrationTab.tsx — generate code + active codes table
├── CourseAssignmentsTab.tsx  — stub placeholder
└── CourseGradebookTab.tsx    — stub placeholder
```

Each tab component receives `courseId` as a prop and manages its own data fetching / loading state.

## Routing

`/dashboard/courses/[id]?tab=roster` (default)

Using `useSearchParams()` in the client component to read/write `tab`. No nested route segments needed — all tabs share the same page component and course header data.

## Backend Dependencies

| Need | Status |
|------|--------|
| `GET /api/v1/courses/{id}` | Exists |
| `GET /api/v1/courses/{id}/students` | Exists |
| `DELETE /api/v1/courses/{id}/students/{userId}` | Exists |
| `POST /api/v1/password-resets/issue` | Exists |
| `POST /api/v1/codes` with courseId | Exists |
| `GET /api/v1/codes` filtered by courseId | Missing (client-filter for now) |
| `GET /api/v1/assignments/courses/{id}` | Exists (for future) |

## Reused Components

- `ResetCodeDialog` — from codes feature, displays reset code with copy + expiry
- `AlertDialog` — shadcn, for Remove Student confirmation
- Design tokens — consistent with existing warm academic palette
