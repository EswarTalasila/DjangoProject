# Frontend Role Coverage Matrix (FR-aligned)

Date: 2026-03-04
Branch: feat/fr-implementation

## Goal
Consolidate all dashboard pages by role across implemented FRs, then run one design polish pass on consistent layout, hierarchy, and interaction quality.

## Current Route Inventory
- `/dashboard`
- `/dashboard/courses`
- `/dashboard/courses/[id]`
- `/dashboard/codes`
- `/dashboard/assessments`
- `/dashboard/assessments/new`
- `/dashboard/assessments/[id]`
- `/dashboard/assessments/[id]/edit`
- `/dashboard/rubrics`
- `/dashboard/rubrics/new`
- `/dashboard/rubrics/[id]`
- `/dashboard/rubrics/[id]/edit`
- `/dashboard/assignments`
- `/dashboard/assignments/new`
- `/dashboard/assignments/[id]`
- `/dashboard/submissions`
- `/dashboard/submissions/[id]`
- `/dashboard/visualizations`
- `/dashboard/visualizations/courses/[courseId]`
- `/dashboard/visualizations/assignments/[assignmentId]`
- `/dashboard/exports`
- `/dashboard/packages`
- `/dashboard/staff`
- `/dashboard/sudo`
- `/dashboard/settings`

## Role Coverage

### STUDENT
- Primary pages:
  - `/dashboard`
  - `/dashboard/courses`
  - `/dashboard/courses/[id]` (assignments tab)
  - `/dashboard/assignments/[id]` (student interaction flow)
  - `/dashboard/submissions`
  - `/dashboard/submissions/[id]`
- Sidebar links:
  - Dashboard, My Courses, My Submissions
- Status: Covered

### TEACHER
- Primary pages:
  - `/dashboard`
  - `/dashboard/courses`, `/dashboard/courses/[id]`
  - `/dashboard/codes`
  - `/dashboard/assessments`, `/dashboard/rubrics`
  - `/dashboard/assignments`, `/dashboard/assignments/new`, `/dashboard/assignments/[id]`
  - `/dashboard/submissions`, `/dashboard/submissions/[id]`
  - `/dashboard/visualizations/*`
  - `/dashboard/exports`, `/dashboard/packages`
- Sidebar links:
  - All above domains exposed
- Status: Covered

### RESEARCHER
- Baseline pages (policy-aligned):
  - `/dashboard`
  - `/dashboard/staff` (teacher roster + researcher-authorized reset ops)
  - `/dashboard/codes` (registration workflows)
  - `/dashboard/visualizations/*` (anonymized by default)
  - `/dashboard/assessments`, `/dashboard/rubrics`
  - `/dashboard/exports`, `/dashboard/packages` (anonymized outputs by default)
- Elevated pages (sudo-gated):
  - `/dashboard/submissions`, `/dashboard/submissions/[id]` requires `VIEW_SUBMISSIONS`
  - Identifiable export/package output requires `EXPORT_IDENTIFIABLE`
- Blocked by default:
  - `/dashboard/courses`, `/dashboard/courses/[id]`
  - `/dashboard/assignments`, `/dashboard/assignments/[id]`
- Sidebar behavior:
  - Submissions link hidden unless `VIEW_SUBMISSIONS`
  - Exports + Package links visible by default; identifiable toggles disabled unless `EXPORT_IDENTIFIABLE`
- Status: Covered with explicit submissions gate

### ADMIN
- Has broad access to all primary dashboard pages listed above.
- Status: Covered

## Known Gaps To Polish (Not Blocking Functional Coverage)
- Visual consistency across list/detail screens (spacing, header density, card/table hierarchy).
- Consistent status chips and timestamp formatting across FR-07/08/09 pages.
- Better cross-linking between assignment detail and submissions review surfaces.
- Package workspace console is now functional; still needs final drag/drop tree UX and visual polish.

## Build/Verification Snapshot
- Frontend build: clean (`next build`)
- Submissions integration tests: clean after researcher `VIEW_SUBMISSIONS` gate changes.

## Execution Plan (Design Pass)
1. Role-first polish order: Researcher -> Teacher -> Student -> Admin.
2. Standardize shell sections on each page:
   - Header block (title + scope + quick actions)
   - Filters block
   - Main data block
   - Empty/error states
3. Normalize interaction primitives:
   - Table row actions
   - Status badge colors/labels
   - Draft/save/submit feedback language
4. Final pass on responsive behavior for all primary role flows.
