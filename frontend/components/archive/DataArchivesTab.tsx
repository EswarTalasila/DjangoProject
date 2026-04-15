'use client';

import { useCallback, useEffect, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { HelpTip } from '@/components/ui/help-tip';
import { StatusBadge } from '@/components/ui/status-badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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

import { listCourses, type CourseSummary } from '@/lib/course-api';
import {
  listAssignmentTemplates,
  type AssignmentTemplate,
} from '@/lib/assignment-template-api';
import {
  downloadAssignmentArchiveBundle,
  generateAssignmentArchiveBundle,
  getAssignmentArchiveBundle,
  listAssignmentsByCourse,
  type Assignment,
  type AssignmentArchiveArtifact,
} from '@/lib/assignment-api';
import {
  archiveCourse,
  restoreCourse,
  purgeCourse,
  archiveAssignmentTemplate,
  restoreAssignmentTemplate,
  purgeAssignmentTemplate,
  archiveAssignment,
  restoreAssignment,
  purgeAssignment,
} from '@/lib/lifecycle-api';
import { toErrorMessage, triggerBrowserDownload } from '@/lib/utils';

// ── Props ──

type DataArchivesTabProps = {
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
};

// ── Sort helpers ──

type SortDirection = 'asc' | 'desc';

/** Clickable column header with sort direction indicator. */
function SortableHeader({
  label,
  field,
  currentSort,
  currentDirection,
  onSort,
}: {
  label: string;
  field: string;
  currentSort: string;
  currentDirection: SortDirection;
  onSort: (field: string) => void;
}) {
  const isActive = currentSort === field;
  return (
    <button
      type="button"
      className="flex items-center gap-1 font-medium hover:text-foreground"
      onClick={() => onSort(field)}
    >
      {label}
      {isActive &&
        (currentDirection === 'asc' ? (
          <ChevronUp className="size-3" />
        ) : (
          <ChevronDown className="size-3" />
        ))}
    </button>
  );
}

/** Generic comparator used by all three tabs. */
function compare(a: unknown, b: unknown, direction: SortDirection): number {
  const aVal = a ?? '';
  const bVal = b ?? '';
  let result = 0;
  if (typeof aVal === 'number' && typeof bVal === 'number') {
    result = aVal - bVal;
  } else {
    result = String(aVal).localeCompare(String(bVal));
  }
  return direction === 'asc' ? result : -result;
}

// ── Component ──

export default function DataArchivesTab({ role }: DataArchivesTabProps) {
  const canManageCourses = role === 'TEACHER' || role === 'ADMIN';
  const canManageAssignmentTemplates = role === 'RESEARCHER' || role === 'ADMIN';
  const canManageAssignments = role === 'TEACHER' || role === 'ADMIN';
  const canPurgeArchivedRecords = role === 'ADMIN';
  const defaultTab = canManageCourses
    ? 'courses'
    : canManageAssignmentTemplates
      ? 'assignment-templates'
      : 'assignments';

  // -- Courses state --
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [showArchivedCourses, setShowArchivedCourses] = useState(false);
  const [busyCourseId, setBusyCourseId] = useState<number | null>(null);

  // -- Assignment templates state --
  const [assignmentTemplates, setAssignmentTemplates] = useState<AssignmentTemplate[]>([]);
  const [loadingAssignmentTemplates, setLoadingAssignmentTemplates] = useState(true);
  const [showArchivedAssignmentTemplates, setShowArchivedAssignmentTemplates] = useState(false);
  const [busyAssignmentTemplateId, setBusyAssignmentTemplateId] = useState<number | null>(null);

  // -- Assignments state --
  const [assignments, setAssignments] = useState<(Assignment & { courseName?: string })[]>([]);
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [showArchivedAssignments, setShowArchivedAssignments] = useState(false);
  const [busyAssignmentId, setBusyAssignmentId] = useState<number | null>(null);
  const [assignmentBundles, setAssignmentBundles] = useState<Record<number, AssignmentArchiveArtifact | null>>({});
  const [busyAssignmentBundleId, setBusyAssignmentBundleId] = useState<number | null>(null);

  // -- Sort state per tab --
  const [courseSortField, setCourseSortField] = useState('name');
  const [courseSortDir, setCourseSortDir] = useState<SortDirection>('asc');

  const [assignmentTemplateSortField, setAssignmentTemplateSortField] = useState('title');
  const [assignmentTemplateSortDir, setAssignmentTemplateSortDir] = useState<SortDirection>('asc');

  const [assignmentSortField, setAssignmentSortField] = useState('title');
  const [assignmentSortDir, setAssignmentSortDir] = useState<SortDirection>('asc');

  // ── Data loading ──

  const loadCourses = useCallback(async (includeArchived: boolean) => {
    setLoadingCourses(true);
    try {
      const data = await listCourses(
        includeArchived ? { includeArchived: true } : undefined,
      );
      setCourses(data);
    } catch {
      toast.error('Failed to load courses.');
    } finally {
      setLoadingCourses(false);
    }
  }, []);

  const loadAssignmentTemplates = useCallback(async (includeArchived: boolean) => {
    setLoadingAssignmentTemplates(true);
    try {
      const data = await listAssignmentTemplates(
        includeArchived ? { includeArchived: true } : undefined,
      );
      setAssignmentTemplates(data);
    } catch {
      toast.error('Failed to load assignment templates.');
    } finally {
      setLoadingAssignmentTemplates(false);
    }
  }, []);

  const loadAssignments = useCallback(async (courseList: CourseSummary[]) => {
    setLoadingAssignments(true);
    try {
      const allAssignments: (Assignment & { courseName?: string })[] = [];
      // Fetch assignments from all visible courses, explicitly including archived rows.
      const results = await Promise.allSettled(
        courseList.map(async (course) => {
          const courseAssignments = await listAssignmentsByCourse(course.id, {
            includeArchived: true,
          });
          return courseAssignments.map((a) => ({ ...a, courseName: course.name }));
        }),
      );
      for (const result of results) {
        if (result.status === 'fulfilled') {
          allAssignments.push(...result.value);
        }
      }
      setAssignments(allAssignments);
    } catch {
      toast.error('Failed to load assignments.');
    } finally {
      setLoadingAssignments(false);
    }
  }, []);

  // Load assignment templates on mount
  useEffect(() => {
    void loadAssignmentTemplates(showArchivedAssignmentTemplates);
  }, [loadAssignmentTemplates, showArchivedAssignmentTemplates]);

  // Load courses on mount and re-fetch when toggle changes
  useEffect(() => {
    void loadCourses(showArchivedCourses);
  }, [showArchivedCourses, loadCourses]);

  // Load assignments once courses are available, always including archived rows so
  // restored courses can still surface archived assignments for review/restore.
  useEffect(() => {
    async function fetchCoursesForAssignments() {
      try {
        const allCourses = await listCourses({ includeArchived: true });
        void loadAssignments(allCourses);
      } catch {
        toast.error('Failed to load assignments.');
        setLoadingAssignments(false);
      }
    }
    void fetchCoursesForAssignments();
  }, [loadAssignments]);

  useEffect(() => {
    const archivedIds = assignments
      .filter((assignment) => assignment.status === 'ARCHIVED')
      .map((assignment) => assignment.id);
    if (archivedIds.length === 0) {
      return;
    }

    let active = true;
    async function loadBundleMetadata() {
      const results = await Promise.allSettled(
        archivedIds.map(async (assignmentId) => {
          const artifact = await getAssignmentArchiveBundle(assignmentId);
          return [assignmentId, artifact] as const;
        }),
      );
      if (!active) return;
      setAssignmentBundles((prev) => {
        const next = { ...prev };
        for (const result of results) {
          if (result.status === 'fulfilled') {
            const [assignmentId, artifact] = result.value;
            next[assignmentId] = artifact;
          }
        }
        return next;
      });
    }

    void loadBundleMetadata();
    return () => {
      active = false;
    };
  }, [assignments]);

  // ── Filtered & sorted data ──

  const displayedCourses = courses;

  const displayedAssignmentTemplates = showArchivedAssignmentTemplates
    ? assignmentTemplates
    : assignmentTemplates.filter((template) => (template.status ?? 'ACTIVE') === 'ACTIVE');

  const displayedAssignments = showArchivedAssignments
    ? assignments
    : assignments.filter((a) => a.status === 'ACTIVE');

  // Sort helpers per entity
  function sortedCourses() {
    return [...displayedCourses].sort((a, b) => {
      const valA =
        courseSortField === 'name'
          ? a.name
          : courseSortField === 'teacher'
            ? (a.teacherName ?? '')
            : courseSortField === 'students'
              ? a.studentCount
              : a.status;
      const valB =
        courseSortField === 'name'
          ? b.name
          : courseSortField === 'teacher'
            ? (b.teacherName ?? '')
            : courseSortField === 'students'
              ? b.studentCount
              : b.status;
      return compare(valA, valB, courseSortDir);
    });
  }

  function sortedAssignmentTemplates() {
    return [...displayedAssignmentTemplates].sort((a, b) => {
      const valA =
        assignmentTemplateSortField === 'title'
          ? a.title
          : assignmentTemplateSortField === 'category'
            ? (a.category ?? '')
            : (a.status ?? 'ACTIVE');
      const valB =
        assignmentTemplateSortField === 'title'
          ? b.title
          : assignmentTemplateSortField === 'category'
            ? (b.category ?? '')
            : (b.status ?? 'ACTIVE');
      return compare(valA, valB, assignmentTemplateSortDir);
    });
  }

  function sortedAssignments() {
    return [...displayedAssignments].sort((a, b) => {
      const valA =
        assignmentSortField === 'title'
          ? a.title
          : assignmentSortField === 'course'
            ? (a.courseName ?? '')
            : assignmentSortField === 'dueDate'
              ? (a.dueAt ?? '')
              : a.status;
      const valB =
        assignmentSortField === 'title'
          ? b.title
          : assignmentSortField === 'course'
            ? (b.courseName ?? '')
            : assignmentSortField === 'dueDate'
              ? (b.dueAt ?? '')
              : b.status;
      return compare(valA, valB, assignmentSortDir);
    });
  }

  // ── Sort toggle handlers ──

  function handleCourseSort(field: string) {
    if (courseSortField === field) {
      setCourseSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setCourseSortField(field);
      setCourseSortDir('asc');
    }
  }

  function handleAssignmentTemplateSort(field: string) {
    if (assignmentTemplateSortField === field) {
      setAssignmentTemplateSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setAssignmentTemplateSortField(field);
      setAssignmentTemplateSortDir('asc');
    }
  }

  function handleAssignmentSort(field: string) {
    if (assignmentSortField === field) {
      setAssignmentSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setAssignmentSortField(field);
      setAssignmentSortDir('asc');
    }
  }

  // ── Course actions ──

  async function handleArchiveCourse(course: CourseSummary) {
    setBusyCourseId(course.id);
    try {
      await archiveCourse(course.id);
      toast.success('Course archived.');
      await loadCourses(showArchivedCourses);
      await refreshAssignments();
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyCourseId(null);
    }
  }

  async function handleRestoreCourse(course: CourseSummary) {
    setBusyCourseId(course.id);
    try {
      await restoreCourse(course.id);
      toast.success('Course restored.');
      await loadCourses(showArchivedCourses);
      await refreshAssignments();
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyCourseId(null);
    }
  }

  async function handlePurgeCourse(course: CourseSummary) {
    setBusyCourseId(course.id);
    try {
      await purgeCourse(course.id);
      toast.success('Course purged.');
      await loadCourses(showArchivedCourses);
      await refreshAssignments();
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyCourseId(null);
    }
  }

  // ── Assignment template actions ──

  async function handleArchiveAssignmentTemplate(template: AssignmentTemplate) {
    setBusyAssignmentTemplateId(template.id);
    try {
      await archiveAssignmentTemplate(template.id);
      toast.success('Assignment template archived.');
      await loadAssignmentTemplates(showArchivedAssignmentTemplates);
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssignmentTemplateId(null);
    }
  }

  async function handleRestoreAssignmentTemplate(template: AssignmentTemplate) {
    setBusyAssignmentTemplateId(template.id);
    try {
      await restoreAssignmentTemplate(template.id);
      toast.success('Assignment template restored.');
      await loadAssignmentTemplates(showArchivedAssignmentTemplates);
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssignmentTemplateId(null);
    }
  }

  async function handlePurgeAssignmentTemplate(template: AssignmentTemplate) {
    setBusyAssignmentTemplateId(template.id);
    try {
      await purgeAssignmentTemplate(template.id);
      toast.success('Assignment template purged.');
      await loadAssignmentTemplates(showArchivedAssignmentTemplates);
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssignmentTemplateId(null);
    }
  }

  // ── Assignment actions ──

  async function refreshAssignments() {
    try {
      const allCourses = await listCourses({ includeArchived: true });
      await loadAssignments(allCourses);
    } catch {
      // Silently fail — not critical
    }
  }

  async function handleArchiveAssignment(assignment: Assignment) {
    setBusyAssignmentId(assignment.id);
    try {
      await archiveAssignment(assignment.id);
      toast.success('Assignment archived.');
      await refreshAssignments();
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssignmentId(null);
    }
  }

  async function handleRestoreAssignment(assignment: Assignment) {
    setBusyAssignmentId(assignment.id);
    try {
      await restoreAssignment(assignment.id);
      toast.success('Assignment restored.');
      await refreshAssignments();
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssignmentId(null);
    }
  }

  async function handlePurgeAssignment(assignment: Assignment) {
    setBusyAssignmentId(assignment.id);
    try {
      await purgeAssignment(assignment.id);
      toast.success('Assignment purged.');
      await refreshAssignments();
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssignmentId(null);
    }
  }

  async function handleGenerateBundle(assignment: Assignment) {
    setBusyAssignmentBundleId(assignment.id);
    try {
      const artifact = await generateAssignmentArchiveBundle(assignment.id);
      setAssignmentBundles((prev) => ({ ...prev, [assignment.id]: artifact }));
      toast.success('Archive bundle generated.');
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssignmentBundleId(null);
    }
  }

  async function handleDownloadBundle(assignment: Assignment) {
    setBusyAssignmentBundleId(assignment.id);
    try {
      const { blob, filename } = await downloadAssignmentArchiveBundle(assignment.id);
      triggerBrowserDownload(blob, filename);
      toast.success('Archive bundle download started.');
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssignmentBundleId(null);
    }
  }

  // ── Render ──

  return (
    <div className="space-y-4">
      {/* Title area with HelpTip */}
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold text-foreground">Archive Records</h2>
        <HelpTip text="Archive keeps records available for later restore or controlled cleanup. Purge permanently removes archived records only when the lifecycle rules allow it, and only admins can do it." />
      </div>

      <Tabs defaultValue={defaultTab}>
        <TabsList className="grid w-full grid-cols-1 gap-1 sm:grid-cols-2 lg:inline-flex lg:w-auto">
          {canManageCourses && <TabsTrigger value="courses">Courses</TabsTrigger>}
          {canManageAssignmentTemplates && (
            <TabsTrigger value="assignment-templates">Assignment Templates</TabsTrigger>
          )}
          {canManageAssignments && <TabsTrigger value="assignments">Assignments</TabsTrigger>}
        </TabsList>

        {/* ── Courses tab ── */}
        {canManageCourses && <TabsContent value="courses" className="space-y-4 pt-4">
          <div className="flex items-center justify-end">
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={showArchivedCourses}
                onCheckedChange={(checked) => setShowArchivedCourses(checked === true)}
              />
              Show archived
              <HelpTip text="Toggle to show or hide archived items in the table." />
            </label>
          </div>

          {loadingCourses ? (
            <p className="text-sm text-muted-foreground">Loading courses...</p>
          ) : displayedCourses.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No archived courses yet. Restoring a course does not restore its assignments, so use the course detail view or assignment archive tools to bring back archived work deliberately.
            </p>
          ) : (
            <div className="space-y-3">
              <div className="grid gap-3 md:hidden">
                {sortedCourses().map((course) => {
                  const isArchived = course.status === 'ARCHIVED';
                  const isBusy = busyCourseId === course.id;
                  return (
                    <div
                      key={course.id}
                      className="rounded-lg border border-border bg-card p-4 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="truncate font-medium text-foreground">{course.name}</h3>
                          <p className="text-sm text-muted-foreground">
                            {course.teacherName ?? 'Unassigned teacher'}
                          </p>
                        </div>
                        <StatusBadge status={isArchived ? 'ARCHIVED' : 'ACTIVE'} />
                      </div>
                      <div className="mt-3 grid gap-2 text-sm text-muted-foreground">
                        <div>Students: {course.studentCount}</div>
                        <div>
                          Restoring a course does not restore its assignments. Use the
                          assignments tab to bring archived work back deliberately.
                        </div>
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {isArchived ? (
                          <>
                            <Button
                              variant="outline"
                              size="xs"
                              disabled={isBusy}
                              onClick={() => void handleRestoreCourse(course)}
                            >
                              {isBusy ? 'Restoring...' : 'Restore'}
                            </Button>
                            {canPurgeArchivedRecords && (
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button variant="destructive" size="xs" disabled={isBusy}>
                                    Purge
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Purge course</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Permanently purge {course.name}? This cannot be undone.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                      variant="destructive"
                                      onClick={() => void handlePurgeCourse(course)}
                                    >
                                      Purge
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            )}
                          </>
                        ) : (
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="secondary" size="xs" disabled={isBusy}>
                                Archive
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Archive course</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Archive {course.name}? This will also archive all assignments in
                                  this course.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction onClick={() => void handleArchiveCourse(course)}>
                                  Archive
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="hidden overflow-x-auto md:block">
                <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="pb-2 pr-4">
                      <SortableHeader
                        label="Name"
                        field="name"
                        currentSort={courseSortField}
                        currentDirection={courseSortDir}
                        onSort={handleCourseSort}
                      />
                    </th>
                    <th className="pb-2 pr-4">
                      <SortableHeader
                        label="Teacher"
                        field="teacher"
                        currentSort={courseSortField}
                        currentDirection={courseSortDir}
                        onSort={handleCourseSort}
                      />
                    </th>
                    <th className="pb-2 pr-4">
                      <SortableHeader
                        label="Students"
                        field="students"
                        currentSort={courseSortField}
                        currentDirection={courseSortDir}
                        onSort={handleCourseSort}
                      />
                    </th>
                    <th className="pb-2 pr-4">
                      <SortableHeader
                        label="Status"
                        field="status"
                        currentSort={courseSortField}
                        currentDirection={courseSortDir}
                        onSort={handleCourseSort}
                      />
                    </th>
                    <th className="pb-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedCourses().map((course) => {
                    const isArchived = course.status === 'ARCHIVED';
                    const isBusy = busyCourseId === course.id;
                    return (
                      <tr
                        key={course.id}
                        className="border-b border-border hover:bg-accent/30 transition-colors"
                      >
                        <td className="py-2 pr-4">{course.name}</td>
                        <td className="py-2 pr-4">{course.teacherName ?? '-'}</td>
                        <td className="py-2 pr-4">{course.studentCount}</td>
                        <td className="py-2 pr-4">
                          <StatusBadge status={isArchived ? 'ARCHIVED' : 'ACTIVE'} />
                        </td>
                        <td className="py-2">
                          <div className="flex items-center gap-2">
                            {isArchived ? (
                              <>
                                <Button
                                  variant="outline"
                                  size="xs"
                                  disabled={isBusy}
                                  onClick={() => void handleRestoreCourse(course)}
                                >
                                  {isBusy ? 'Restoring...' : 'Restore'}
                                </Button>
                                {canPurgeArchivedRecords && (
                                  <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                      <Button variant="destructive" size="xs" disabled={isBusy}>
                                        Purge
                                      </Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                      <AlertDialogHeader>
                                        <AlertDialogTitle>Purge course</AlertDialogTitle>
                                        <AlertDialogDescription>
                                          Permanently purge {course.name}? This cannot be undone.
                                          All archived course data will be removed.
                                        </AlertDialogDescription>
                                      </AlertDialogHeader>
                                      <AlertDialogFooter>
                                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                                        <AlertDialogAction
                                          variant="destructive"
                                          onClick={() => void handlePurgeCourse(course)}
                                        >
                                          Purge
                                        </AlertDialogAction>
                                      </AlertDialogFooter>
                                    </AlertDialogContent>
                                  </AlertDialog>
                                )}
                              </>
                            ) : (
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button variant="secondary" size="xs" disabled={isBusy}>
                                    Archive
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Archive course</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Archive {course.name}? This will also archive all assignments
                                      in this course. Students will no longer be able to submit
                                      work.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                      onClick={() => void handleArchiveCourse(course)}
                                    >
                                      Archive
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                </table>
              </div>
            </div>
          )}
        </TabsContent>}

        {/* ── Assignment templates tab ── */}
        {canManageAssignmentTemplates && <TabsContent value="assignment-templates" className="space-y-4 pt-4">
          <div className="flex items-center justify-end">
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={showArchivedAssignmentTemplates}
                onCheckedChange={(checked) => setShowArchivedAssignmentTemplates(checked === true)}
              />
              Show archived
              <HelpTip text="Toggle to show or hide archived items in the table." />
            </label>
          </div>

          {loadingAssignmentTemplates ? (
            <p className="text-sm text-muted-foreground">Loading assignment templates...</p>
          ) : displayedAssignmentTemplates.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No archived assignment templates yet. Used templates should be archived instead of edited or deleted in place.
            </p>
          ) : (
            <div className="space-y-3">
              <div className="grid gap-3 md:hidden">
                {sortedAssignmentTemplates().map((template) => {
                  const status = template.status ?? 'ACTIVE';
                  const isArchived = status === 'ARCHIVED';
                  const isDraft = status === 'DRAFT';
                  const isBusy = busyAssignmentTemplateId === template.id;
                  return (
                    <div
                      key={template.id}
                      className="rounded-lg border border-border bg-card p-4 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="truncate font-medium text-foreground">{template.title}</h3>
                          <p className="text-sm text-muted-foreground">
                            {template.category ?? 'Uncategorized'}
                          </p>
                        </div>
                        <StatusBadge status={status} />
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {isArchived ? (
                          <>
                            <Button
                              variant="outline"
                              size="xs"
                              disabled={isBusy}
                              onClick={() => void handleRestoreAssignmentTemplate(template)}
                            >
                              {isBusy ? 'Restoring...' : 'Restore'}
                            </Button>
                            {canPurgeArchivedRecords && (
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button variant="destructive" size="xs" disabled={isBusy}>
                                    Purge
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Purge assignment template</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Permanently purge {template.title}? This cannot be undone.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                      variant="destructive"
                                      onClick={() => void handlePurgeAssignmentTemplate(template)}
                                    >
                                      Purge
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            )}
                          </>
                        ) : isDraft ? (
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="destructive" size="xs" disabled={isBusy}>
                                Delete Draft
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Delete draft template</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Permanently delete the draft {template.title}? This cannot be
                                  undone.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                  variant="destructive"
                                  onClick={() => void handlePurgeAssignmentTemplate(template)}
                                >
                                  Delete Draft
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        ) : (
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="secondary" size="xs" disabled={isBusy}>
                                Archive
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Archive assignment template</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Archive {template.title}? It will no longer appear in active
                                  views.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => void handleArchiveAssignmentTemplate(template)}
                                >
                                  Archive
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="hidden overflow-x-auto md:block">
                <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="pb-2 pr-4">
                      <SortableHeader
                        label="Title"
                        field="title"
                        currentSort={assignmentTemplateSortField}
                        currentDirection={assignmentTemplateSortDir}
                        onSort={handleAssignmentTemplateSort}
                      />
                    </th>
                    <th className="pb-2 pr-4">
                      <SortableHeader
                        label="Category"
                        field="category"
                        currentSort={assignmentTemplateSortField}
                        currentDirection={assignmentTemplateSortDir}
                        onSort={handleAssignmentTemplateSort}
                      />
                    </th>
                    <th className="pb-2 pr-4">
                      <SortableHeader
                        label="Status"
                        field="status"
                        currentSort={assignmentTemplateSortField}
                        currentDirection={assignmentTemplateSortDir}
                        onSort={handleAssignmentTemplateSort}
                      />
                    </th>
                    <th className="pb-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedAssignmentTemplates().map((template) => {
                    const status = template.status ?? 'ACTIVE';
                    const isArchived = status === 'ARCHIVED';
                    const isDraft = status === 'DRAFT';
                    const isBusy = busyAssignmentTemplateId === template.id;
                    return (
                      <tr
                        key={template.id}
                        className="border-b border-border hover:bg-accent/30 transition-colors"
                      >
                        <td className="py-2 pr-4">{template.title}</td>
                        <td className="py-2 pr-4">{template.category ?? '-'}</td>
                        <td className="py-2 pr-4">
                          <StatusBadge status={status} />
                        </td>
                        <td className="py-2">
                          <div className="flex items-center gap-2">
                            {isArchived ? (
                              <>
                                <Button
                                  variant="outline"
                                  size="xs"
                                  disabled={isBusy}
                                  onClick={() => void handleRestoreAssignmentTemplate(template)}
                                >
                                  {isBusy ? 'Restoring...' : 'Restore'}
                                </Button>
                                {canPurgeArchivedRecords && (
                                  <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                      <Button variant="destructive" size="xs" disabled={isBusy}>
                                        Purge
                                      </Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                      <AlertDialogHeader>
                                        <AlertDialogTitle>Purge assignment template</AlertDialogTitle>
                                        <AlertDialogDescription>
                                          Permanently purge {template.title}? This cannot be
                                          undone.
                                        </AlertDialogDescription>
                                      </AlertDialogHeader>
                                      <AlertDialogFooter>
                                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                                        <AlertDialogAction
                                          variant="destructive"
                                          onClick={() => void handlePurgeAssignmentTemplate(template)}
                                        >
                                          Purge
                                        </AlertDialogAction>
                                      </AlertDialogFooter>
                                    </AlertDialogContent>
                                  </AlertDialog>
                                )}
                              </>
                            ) : isDraft ? (
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button variant="destructive" size="xs" disabled={isBusy}>
                                    Delete Draft
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Delete draft template</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Permanently delete the draft {template.title}? This cannot be
                                      undone.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                      variant="destructive"
                                      onClick={() => void handlePurgeAssignmentTemplate(template)}
                                    >
                                      Delete Draft
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            ) : (
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button variant="secondary" size="xs" disabled={isBusy}>
                                    Archive
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>
                                      Archive assignment template
                                    </AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Archive {template.title}? It will no longer appear in active
                                      views.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                      onClick={() => void handleArchiveAssignmentTemplate(template)}
                                    >
                                      Archive
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                </table>
              </div>
            </div>
          )}
        </TabsContent>}

        {/* ── Assignments tab ── */}
        {canManageAssignments && <TabsContent value="assignments" className="space-y-4 pt-4">
          <div className="flex items-center justify-end">
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={showArchivedAssignments}
                onCheckedChange={(checked) => setShowArchivedAssignments(checked === true)}
              />
              Show archived
              <HelpTip text="Toggle to show or hide archived items in the table." />
            </label>
          </div>

          {loadingAssignments ? (
            <p className="text-sm text-muted-foreground">Loading assignments...</p>
          ) : displayedAssignments.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No archived assignments yet. Archived assignments linked to restored courses will appear here and can be restored individually.
            </p>
          ) : (
            <div className="space-y-3">
              <div className="grid gap-3 md:hidden">
                {sortedAssignments().map((assignment, index) => {
                  const isArchived = assignment.status === 'ARCHIVED';
                  const isBusy = busyAssignmentId === assignment.id;
                  const isBundleBusy = busyAssignmentBundleId === assignment.id;
                  const bundle = assignmentBundles[assignment.id] ?? null;
                  return (
                    <div
                      key={`${assignment.courseId ?? 'none'}-${assignment.id}-${index}`}
                      className="rounded-lg border border-border bg-card p-4 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="truncate font-medium text-foreground">{assignment.title}</h3>
                          <p className="text-sm text-muted-foreground">
                            {assignment.courseName ?? 'No course'} •{' '}
                            {assignment.dueAt
                              ? new Date(assignment.dueAt).toLocaleDateString()
                              : 'No due date'}
                          </p>
                        </div>
                        <StatusBadge status={isArchived ? 'ARCHIVED' : 'ACTIVE'} />
                      </div>
                      {isArchived && (
                        <p className="mt-2 text-sm text-muted-foreground">
                          {bundle
                            ? `Bundle ready • ${bundle.filename}`
                            : 'Generate a bundle when you need a frozen handoff for this archived assignment.'}
                        </p>
                      )}
                      <div className="mt-4 flex flex-wrap gap-2">
                        {isArchived ? (
                          <>
                            <Button
                              variant="outline"
                              size="xs"
                              disabled={isBusy}
                              onClick={() => void handleRestoreAssignment(assignment)}
                            >
                              {isBusy ? 'Restoring...' : 'Restore'}
                            </Button>
                            <Button
                              variant={bundle ? 'outline' : 'secondary'}
                              size="xs"
                              disabled={isBundleBusy}
                              onClick={() =>
                                void (bundle
                                  ? handleDownloadBundle(assignment)
                                  : handleGenerateBundle(assignment))
                              }
                            >
                              {isBundleBusy
                                ? bundle
                                  ? 'Downloading...'
                                  : 'Generating...'
                                : bundle
                                  ? 'Download Bundle'
                                  : 'Generate Bundle'}
                            </Button>
                            {canPurgeArchivedRecords && (
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button variant="destructive" size="xs" disabled={isBusy}>
                                    Purge
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Purge assignment</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Permanently purge {assignment.title}? This cannot be undone.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                      variant="destructive"
                                      onClick={() => void handlePurgeAssignment(assignment)}
                                    >
                                      Purge
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            )}
                          </>
                        ) : (
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="secondary" size="xs" disabled={isBusy}>
                                Archive
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Archive assignment</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Archive {assignment.title}? Students will no longer be able to
                                  submit responses.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => void handleArchiveAssignment(assignment)}
                                >
                                  Archive
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="hidden overflow-x-auto md:block">
                <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="pb-2 pr-4">
                      <SortableHeader
                        label="Title"
                        field="title"
                        currentSort={assignmentSortField}
                        currentDirection={assignmentSortDir}
                        onSort={handleAssignmentSort}
                      />
                    </th>
                    <th className="pb-2 pr-4">
                      <SortableHeader
                        label="Course"
                        field="course"
                        currentSort={assignmentSortField}
                        currentDirection={assignmentSortDir}
                        onSort={handleAssignmentSort}
                      />
                    </th>
                    <th className="pb-2 pr-4">
                      <SortableHeader
                        label="Due Date"
                        field="dueDate"
                        currentSort={assignmentSortField}
                        currentDirection={assignmentSortDir}
                        onSort={handleAssignmentSort}
                      />
                    </th>
                    <th className="pb-2 pr-4">
                      <SortableHeader
                        label="Status"
                        field="status"
                        currentSort={assignmentSortField}
                        currentDirection={assignmentSortDir}
                        onSort={handleAssignmentSort}
                      />
                    </th>
                    <th className="pb-2 pr-4 font-medium">Bundle</th>
                    <th className="pb-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedAssignments().map((assignment, index) => {
                    const isArchived = assignment.status === 'ARCHIVED';
                    const isBusy = busyAssignmentId === assignment.id;
                    const isBundleBusy = busyAssignmentBundleId === assignment.id;
                    const bundle = assignmentBundles[assignment.id] ?? null;
                    return (
                      <tr
                        key={`${assignment.courseId ?? 'none'}-${assignment.id}-${index}`}
                        className="border-b border-border hover:bg-accent/30 transition-colors"
                      >
                        <td className="py-2 pr-4">{assignment.title}</td>
                        <td className="py-2 pr-4">{assignment.courseName ?? '-'}</td>
                        <td className="py-2 pr-4">
                          {assignment.dueAt
                            ? new Date(assignment.dueAt).toLocaleDateString()
                            : '-'}
                        </td>
                        <td className="py-2 pr-4">
                          <StatusBadge status={isArchived ? 'ARCHIVED' : 'ACTIVE'} />
                        </td>
                        <td className="py-2 pr-4">
                          {isArchived ? (
                            bundle ? (
                              <Button
                                variant="outline"
                                size="xs"
                                disabled={isBundleBusy}
                                onClick={() => void handleDownloadBundle(assignment)}
                              >
                                {isBundleBusy ? 'Downloading...' : 'Download Bundle'}
                              </Button>
                            ) : (
                              <Button
                                variant="secondary"
                                size="xs"
                                disabled={isBundleBusy}
                                onClick={() => void handleGenerateBundle(assignment)}
                              >
                                {isBundleBusy ? 'Generating...' : 'Generate Bundle'}
                              </Button>
                            )
                          ) : (
                            <span className="text-xs text-muted-foreground">
                              Available after archive
                            </span>
                          )}
                        </td>
                        <td className="py-2">
                          <div className="flex items-center gap-2">
                            {isArchived ? (
                              <>
                                <Button
                                  variant="outline"
                                  size="xs"
                                  disabled={isBusy}
                                  onClick={() => void handleRestoreAssignment(assignment)}
                                >
                                  {isBusy ? 'Restoring...' : 'Restore'}
                                </Button>
                                {canPurgeArchivedRecords && (
                                  <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                      <Button variant="destructive" size="xs" disabled={isBusy}>
                                        Purge
                                      </Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                      <AlertDialogHeader>
                                        <AlertDialogTitle>Purge assignment</AlertDialogTitle>
                                        <AlertDialogDescription>
                                          Permanently purge {assignment.title}? This cannot be
                                          undone.
                                        </AlertDialogDescription>
                                      </AlertDialogHeader>
                                      <AlertDialogFooter>
                                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                                        <AlertDialogAction
                                          variant="destructive"
                                          onClick={() => void handlePurgeAssignment(assignment)}
                                        >
                                          Purge
                                        </AlertDialogAction>
                                      </AlertDialogFooter>
                                    </AlertDialogContent>
                                  </AlertDialog>
                                )}
                              </>
                            ) : (
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button variant="secondary" size="xs" disabled={isBusy}>
                                    Archive
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Archive assignment</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Archive {assignment.title}? Students will no longer be able to
                                      submit responses.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                      onClick={() => void handleArchiveAssignment(assignment)}
                                    >
                                      Archive
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                </table>
              </div>
            </div>
          )}
        </TabsContent>}
      </Tabs>
    </div>
  );
}
