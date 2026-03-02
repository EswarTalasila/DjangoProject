# Course Detail Tabs + Sidebar Cleanup — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure `/dashboard/courses/[id]` into a 4-tab layout (Roster, Registration, Assignments, Gradebook), remove Self Assessment from teacher sidebar, and implement Roster + Registration tabs fully.

**Architecture:** CourseDetailView becomes a thin shell (header + tab bar + tab router). Each tab is an independent component that lazy-loads its own data. URL-driven via `?tab=` query param. Existing student table logic extracted into CourseRosterTab with added Issue Reset. CourseRegistrationTab generates codes and lists active ones via client-side filtering.

**Tech Stack:** Next.js 15 App Router, React client components, `useSearchParams()`, shadcn/ui, design tokens, existing `registration-code-api.ts` + `password-reset-api.ts`.

---

### Task 1: Remove Self Assessment from teacher sidebar

**Files:**
- Modify: `frontend/components/layout/sidebarWrapper.tsx:55`

**Step 1: Remove the Self Assessment nav item**

Delete line 55:
```tsx
// DELETE THIS LINE:
{ type: "link", label: "Self Assessment", href: "/dashboard/teacher/self" },
```

Also remove the stale TODO comment on line 50:
```tsx
// DELETE THIS LINE:
//TODO: Further implementation of teacher side is required. They need a way to view students and add students to their course
```

**Step 2: Build to verify**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds, no errors.

**Step 3: Commit**

```bash
git add frontend/components/layout/sidebarWrapper.tsx
git commit -m "refactor(frontend): remove Self Assessment from teacher sidebar"
```

---

### Task 2: Create stub tab components (Assignments + Gradebook)

**Files:**
- Create: `frontend/components/courses/CourseAssignmentsTab.tsx`
- Create: `frontend/components/courses/CourseGradebookTab.tsx`

**Step 1: Create CourseAssignmentsTab stub**

```tsx
'use client';

type CourseAssignmentsTabProps = { courseId: number };

export default function CourseAssignmentsTab({ courseId }: CourseAssignmentsTabProps) {
  return (
    <div className="rounded-sm border border-border bg-card p-8 text-center">
      <p className="text-sm text-muted-foreground">
        Assignments for this course will appear here.
      </p>
    </div>
  );
}
```

**Step 2: Create CourseGradebookTab stub**

```tsx
'use client';

type CourseGradebookTabProps = { courseId: number };

export default function CourseGradebookTab({ courseId }: CourseGradebookTabProps) {
  return (
    <div className="rounded-sm border border-border bg-card p-8 text-center">
      <p className="text-sm text-muted-foreground">
        Gradebook for this course will appear here.
      </p>
    </div>
  );
}
```

**Step 3: Build to verify**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds (components not imported yet, but no errors).

**Step 4: Commit**

```bash
git add frontend/components/courses/CourseAssignmentsTab.tsx frontend/components/courses/CourseGradebookTab.tsx
git commit -m "feat(frontend): add stub CourseAssignmentsTab and CourseGradebookTab"
```

---

### Task 3: Extract CourseRosterTab from CourseDetailView

This is the core extraction. Move the entire students table + remove logic out of CourseDetailView into its own component, then add Issue Reset.

**Files:**
- Create: `frontend/components/courses/CourseRosterTab.tsx`
- Modify: `frontend/components/courses/CourseDetailView.tsx`

**Step 1: Create CourseRosterTab with existing roster + Issue Reset**

The new component receives `courseId` and `canManage` as props. It manages its own data fetching (lazy-load), plus the Issue Reset dialog state.

```tsx
'use client';

import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ResetCodeDialog } from '@/components/codes/ResetCodeDialog';
import {
  listStudentsInCourse,
  removeStudentFromCourse,
  type CourseStudent,
} from '@/lib/course-api';
import { issuePasswordResetCode } from '@/lib/password-reset-api';

type ApiError = { response?: { data?: { detail?: string } } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

function formatDate(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

type CourseRosterTabProps = {
  courseId: number;
  canManage: boolean;
};

export default function CourseRosterTab({ courseId, canManage }: CourseRosterTabProps) {
  const [students, setStudents] = useState<CourseStudent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [removingStudentId, setRemovingStudentId] = useState<number | null>(null);

  // Issue Reset state
  const [isResetting, setIsResetting] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [resetCode, setResetCode] = useState<string | null>(null);
  const [resetTargetName, setResetTargetName] = useState<string | null>(null);
  const [resetExpiresAt, setResetExpiresAt] = useState<string | null>(null);

  const loadStudents = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await listStudentsInCourse(courseId);
      setStudents(data);
    } catch {
      setLoadError('Failed to load students.');
    } finally {
      setIsLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    setIsLoading(true);
    void loadStudents();
  }, [loadStudents]);

  async function handleRemoveStudent(studentId: number, studentName: string) {
    setRemovingStudentId(studentId);
    try {
      await removeStudentFromCourse(courseId, studentId);
      toast.success(`Student "${studentName}" removed.`);
      await loadStudents();
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to remove student.'));
    } finally {
      setRemovingStudentId(null);
    }
  }

  async function handleIssueReset(studentId: number, studentName: string) {
    setIsResetting(true);
    try {
      const result = await issuePasswordResetCode(studentId);
      setResetCode(result.resetCode);
      setResetTargetName(studentName);
      setResetExpiresAt(result.expiresAt);
      setResetDialogOpen(true);
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to issue reset code.'));
    } finally {
      setIsResetting(false);
    }
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground py-4">Loading roster...</p>;
  }

  if (loadError) {
    return <p className="text-sm text-destructive py-4">{loadError}</p>;
  }

  return (
    <>
      {students.length === 0 ? (
        <div className="rounded-sm border border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No students enrolled in this course.
          </p>
        </div>
      ) : (
        <div className="rounded-sm border border-border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted border-b border-border">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Name
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Username
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Enrolled
                </TableHead>
                {canManage && (
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Actions
                  </TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {students.map((student) => (
                <TableRow
                  key={student.id}
                  className="even:bg-muted/50 hover:bg-accent transition-colors"
                >
                  <TableCell className="font-medium text-sm text-foreground">
                    {student.name}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {student.username}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(student.enrolledAt)}
                  </TableCell>
                  {canManage && (
                    <TableCell className="space-x-2">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={isResetting}
                        onClick={() => void handleIssueReset(student.id, student.name)}
                      >
                        Issue Reset
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:text-destructive"
                            disabled={removingStudentId === student.id}
                          >
                            {removingStudentId === student.id ? 'Removing...' : 'Remove'}
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Remove Student</AlertDialogTitle>
                            <AlertDialogDescription>
                              Are you sure you want to remove{' '}
                              <span className="font-medium">{student.name}</span>{' '}
                              from this course? This action cannot be undone.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => void handleRemoveStudent(student.id, student.name)}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            >
                              Remove
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <ResetCodeDialog
        open={resetDialogOpen}
        onOpenChange={setResetDialogOpen}
        code={resetCode}
        targetName={resetTargetName}
        expiresAt={resetExpiresAt}
      />
    </>
  );
}
```

**Step 2: Build to verify**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 3: Commit**

```bash
git add frontend/components/courses/CourseRosterTab.tsx
git commit -m "feat(frontend): extract CourseRosterTab with Issue Reset support"
```

---

### Task 4: Create CourseRegistrationTab

**Files:**
- Create: `frontend/components/courses/CourseRegistrationTab.tsx`

**Step 1: Create the component**

This tab generates student registration codes for the course and lists active ones. It fetches the teacher's STUDENT codes via `listRegistrationCodes({ codeType: 'STUDENT' })` and client-filters by `courseId`.

```tsx
'use client';

import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  createStudentRegistrationCode,
  listRegistrationCodes,
  type RegistrationCode,
} from '@/lib/registration-code-api';

type ApiError = { response?: { data?: { detail?: string } } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

type CourseRegistrationTabProps = {
  courseId: number;
};

export default function CourseRegistrationTab({ courseId }: CourseRegistrationTabProps) {
  const [codes, setCodes] = useState<RegistrationCode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedCode, setGeneratedCode] = useState<string | null>(null);

  const loadCodes = useCallback(async () => {
    setLoadError(null);
    try {
      const response = await listRegistrationCodes({ codeType: 'STUDENT' });
      const filtered = response.results.filter(
        (c) => c.courseId === courseId && c.isActive,
      );
      setCodes(filtered);
    } catch {
      setLoadError('Failed to load registration codes.');
    } finally {
      setIsLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    setIsLoading(true);
    void loadCodes();
  }, [loadCodes]);

  async function handleGenerate() {
    setIsGenerating(true);
    setGeneratedCode(null);
    try {
      const code = await createStudentRegistrationCode(courseId);
      setGeneratedCode(code);
      toast.success('Registration code generated.');
      await loadCodes();
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to generate registration code.'));
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleCopyCode(code: string) {
    await navigator.clipboard.writeText(code);
    toast.success('Code copied to clipboard.');
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground py-4">Loading codes...</p>;
  }

  if (loadError) {
    return <p className="text-sm text-destructive py-4">{loadError}</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Generate registration codes for students to join this course.
        </p>
        <Button onClick={() => void handleGenerate()} disabled={isGenerating}>
          {isGenerating ? 'Generating...' : 'Generate Code'}
        </Button>
      </div>

      {generatedCode && (
        <div className="rounded-sm border border-brand-gold bg-brand-gold/10 p-4">
          <p className="text-xs font-medium uppercase text-muted-foreground mb-1">New Code</p>
          <div className="flex items-center gap-3">
            <p className="font-mono text-lg font-semibold tracking-wide text-foreground">
              {generatedCode}
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => void handleCopyCode(generatedCode)}
            >
              Copy
            </Button>
          </div>
        </div>
      )}

      {codes.length === 0 ? (
        <div className="rounded-sm border border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No active registration codes for this course.
          </p>
        </div>
      ) : (
        <div className="rounded-sm border border-border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted border-b border-border">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Code Prefix
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Uses
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Expires
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Created
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {codes.map((code) => (
                <TableRow
                  key={code.id}
                  className="even:bg-muted/50 hover:bg-accent transition-colors"
                >
                  <TableCell className="font-mono text-sm text-foreground">
                    {code.codePrefix}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {code.timesUsed} / {code.maxUses}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(code.expiresAt)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(code.createdAt)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
```

**Step 2: Build to verify**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 3: Commit**

```bash
git add frontend/components/courses/CourseRegistrationTab.tsx
git commit -m "feat(frontend): add CourseRegistrationTab with code gen and active codes list"
```

---

### Task 5: Rewrite CourseDetailView as tab shell

**Files:**
- Modify: `frontend/components/courses/CourseDetailView.tsx`

**Step 1: Rewrite CourseDetailView**

Replace the entire file. The new version:
- Keeps the header (back link, course name with inline edit, metadata)
- Adds a tab bar below the header
- Uses `useSearchParams()` to read/write `?tab=` (default: `roster`)
- Lazy-renders the active tab component
- Removes all student table code (now in CourseRosterTab)
- Removes the Danger Zone section (disabled Delete Course button adds no value)

```tsx
'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { ArrowLeft, Check, Pencil, X } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { getCourse, updateCourse, type CourseSummary } from '@/lib/course-api';
import CourseRosterTab from './CourseRosterTab';
import CourseRegistrationTab from './CourseRegistrationTab';
import CourseAssignmentsTab from './CourseAssignmentsTab';
import CourseGradebookTab from './CourseGradebookTab';

type ApiError = { response?: { data?: { detail?: string } } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

const TABS = ['roster', 'registration', 'assignments', 'gradebook'] as const;
type Tab = (typeof TABS)[number];

const TAB_LABELS: Record<Tab, string> = {
  roster: 'Roster',
  registration: 'Registration',
  assignments: 'Assignments',
  gradebook: 'Gradebook',
};

type CourseDetailViewProps = {
  courseId: number;
  userRole: 'TEACHER' | 'RESEARCHER';
  userId: number;
};

export default function CourseDetailView({
  courseId,
  userRole,
}: CourseDetailViewProps) {
  const canManage = userRole === 'TEACHER';
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const rawTab = searchParams.get('tab');
  const activeTab: Tab = TABS.includes(rawTab as Tab) ? (rawTab as Tab) : 'roster';

  function setTab(tab: Tab) {
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', tab);
    router.replace(`${pathname}?${params.toString()}`);
  }

  // Course header data
  const [course, setCourse] = useState<CourseSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Inline name editing
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState('');
  const [isSavingName, setIsSavingName] = useState(false);

  const loadCourse = useCallback(async () => {
    setLoadError(null);
    try {
      const courseData = await getCourse(courseId);
      setCourse(courseData);
    } catch {
      setLoadError('Failed to load course details.');
    } finally {
      setIsLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    setIsLoading(true);
    void loadCourse();
  }, [loadCourse]);

  function startEditingName() {
    if (!course) return;
    setEditedName(course.name);
    setIsEditingName(true);
  }

  function cancelEditingName() {
    setIsEditingName(false);
    setEditedName('');
  }

  async function saveName() {
    const trimmed = editedName.trim();
    if (!trimmed || !course) return;
    setIsSavingName(true);
    try {
      const updated = await updateCourse(courseId, trimmed);
      setCourse(updated);
      setIsEditingName(false);
      toast.success('Course name updated.');
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to update course name.'));
    } finally {
      setIsSavingName(false);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6 p-6 max-w-6xl mx-auto">
        <p className="text-sm text-muted-foreground">Loading course...</p>
      </div>
    );
  }

  if (loadError || !course) {
    return (
      <div className="space-y-6 p-6 max-w-6xl mx-auto">
        <Link
          href="/dashboard/courses"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Courses
        </Link>
        <p className="text-sm text-destructive">
          {loadError || 'Course not found.'}
        </p>
      </div>
    );
  }

  // Which tabs to show — teachers see all, researchers see roster only
  const visibleTabs: Tab[] = canManage
    ? [...TABS]
    : ['roster'];

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      {/* Back link */}
      <Link
        href="/dashboard/courses"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Courses
      </Link>

      {/* Header */}
      <div className="space-y-1">
        {isEditingName ? (
          <div className="flex items-center gap-2">
            <Input
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !isSavingName) void saveName();
                if (e.key === 'Escape') cancelEditingName();
              }}
              disabled={isSavingName}
              className="text-2xl font-bold h-auto py-1 max-w-md"
              autoFocus
            />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => void saveName()}
              disabled={isSavingName || !editedName.trim()}
              aria-label="Save name"
            >
              <Check className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={cancelEditingName}
              disabled={isSavingName}
              aria-label="Cancel editing"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight text-foreground">
              {course.name}
            </h1>
            {canManage && (
              <Button
                variant="ghost"
                size="icon"
                onClick={startEditingName}
                aria-label="Edit course name"
              >
                <Pencil className="h-4 w-4" />
              </Button>
            )}
          </div>
        )}
        <p className="text-sm text-muted-foreground">
          {course.teacherName ? `Teacher: ${course.teacherName}` : ''}
          {course.teacherName && course.createdAt
            ? ' \u00b7 '
            : ''}
          {course.createdAt
            ? `Created ${new Date(course.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`
            : ''}
        </p>
      </div>

      {/* Tab bar */}
      <div className="border-b border-border">
        <nav className="flex gap-4" aria-label="Course tabs">
          {visibleTabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setTab(tab)}
              className={`pb-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === tab
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content (lazy-loaded) */}
      {activeTab === 'roster' && (
        <CourseRosterTab courseId={courseId} canManage={canManage} />
      )}
      {activeTab === 'registration' && canManage && (
        <CourseRegistrationTab courseId={courseId} />
      )}
      {activeTab === 'assignments' && canManage && (
        <CourseAssignmentsTab courseId={courseId} />
      )}
      {activeTab === 'gradebook' && canManage && (
        <CourseGradebookTab courseId={courseId} />
      )}
    </div>
  );
}
```

**Step 2: Build to verify**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 3: Commit**

```bash
git add frontend/components/courses/CourseDetailView.tsx
git commit -m "feat(frontend): rewrite CourseDetailView as tabbed shell with 4 tabs

Roster and Registration tabs fully functional. Assignments and
Gradebook are stubs. URL-driven via ?tab= query param."
```

---

### Task 6: Clean up unused imports in CourseDetailView

**Files:**
- Modify: `frontend/components/courses/CourseDetailView.tsx`

**Step 1: Verify no unused imports remain after rewrite**

After the Task 5 rewrite, the following imports from the old file should already be gone:
- `AlertDialog` and all sub-imports (moved to CourseRosterTab)
- `Table` and all sub-imports (moved to CourseRosterTab)
- `listStudentsInCourse`, `removeStudentFromCourse`, `CourseStudent` (moved to CourseRosterTab)

Check that the rewritten file only imports what it uses. Run build to confirm.

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds with no unused import warnings.

**Step 2: Commit (only if changes were needed)**

```bash
git add frontend/components/courses/CourseDetailView.tsx
git commit -m "refactor(frontend): clean up unused imports in CourseDetailView"
```

---

### Task 7: Final build verification and summary commit

**Step 1: Full build**

Run: `cd frontend && npx next build 2>&1 | tail -10`
Expected: Build succeeds, `/dashboard/courses/[id]` listed as dynamic route.

**Step 2: Verify routing works**

Confirm these paths work:
- `/dashboard/courses/1` → defaults to Roster tab
- `/dashboard/courses/1?tab=registration` → shows Registration tab
- `/dashboard/courses/1?tab=assignments` → shows stub
- `/dashboard/courses/1?tab=gradebook` → shows stub

**Step 3: Run backend tests to ensure no regressions**

Run: `docker exec eel-backend python -m pytest 2>&1 | tail -5`
Expected: All tests pass (no backend changes).
