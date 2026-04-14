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
import { listAssignmentsByCourse, type Assignment } from '@/lib/assignment-api';
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
import { toErrorMessage } from '@/lib/utils';

// ── Props ──

type DataArchivesTabProps = {
  role: 'RESEARCHER' | 'ADMIN';
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

// eslint-disable-next-line @typescript-eslint/no-unused-vars -- reserved for admin-only purge gating
export default function DataArchivesTab({ role }: DataArchivesTabProps) {
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

  const loadAssignmentTemplates = useCallback(async () => {
    setLoadingAssignmentTemplates(true);
    try {
      const data = await listAssignmentTemplates();
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
      // Fetch assignments from all courses (including archived ones to get archived assignments)
      const results = await Promise.allSettled(
        courseList.map(async (course) => {
          const courseAssignments = await listAssignmentsByCourse(course.id);
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
    void loadAssignmentTemplates();
  }, [loadAssignmentTemplates]);

  // Load courses on mount and re-fetch when toggle changes
  useEffect(() => {
    void loadCourses(showArchivedCourses);
  }, [showArchivedCourses, loadCourses]);

  // Load assignments once courses are available
  // We always fetch with includeArchived for assignment aggregation
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

  async function handleDeleteCourse(course: CourseSummary) {
    setBusyCourseId(course.id);
    try {
      await purgeCourse(course.id);
      toast.success('Course deleted.');
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
      await loadAssignmentTemplates();
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
      await loadAssignmentTemplates();
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssignmentTemplateId(null);
    }
  }

  async function handleDeleteAssignmentTemplate(template: AssignmentTemplate) {
    setBusyAssignmentTemplateId(template.id);
    try {
      await purgeAssignmentTemplate(template.id);
      toast.success('Assignment template deleted.');
      await loadAssignmentTemplates();
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

  async function handleDeleteAssignment(assignment: Assignment) {
    setBusyAssignmentId(assignment.id);
    try {
      await purgeAssignment(assignment.id);
      toast.success('Assignment deleted.');
      await refreshAssignments();
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssignmentId(null);
    }
  }

  // ── Render ──

  return (
    <div className="space-y-4">
      {/* Title area with HelpTip */}
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold text-foreground">Data Archives</h2>
        <HelpTip text="Archiving hides items from active views but preserves all data. Items can be restored later. Deleting permanently removes an item and all associated data." />
      </div>

      <Tabs defaultValue="courses">
        <TabsList>
          <TabsTrigger value="courses">Courses</TabsTrigger>
          <TabsTrigger value="assignment-templates">Assignment Templates</TabsTrigger>
          <TabsTrigger value="assignments">Assignments</TabsTrigger>
        </TabsList>

        {/* ── Courses tab ── */}
        <TabsContent value="courses" className="space-y-4 pt-4">
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
              No archived courses. Active courses can be archived from their detail pages or using
              the table actions.
            </p>
          ) : (
            <div className="overflow-x-auto">
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
                                <AlertDialog>
                                  <AlertDialogTrigger asChild>
                                    <Button variant="destructive" size="xs" disabled={isBusy}>
                                      Delete
                                    </Button>
                                  </AlertDialogTrigger>
                                  <AlertDialogContent>
                                    <AlertDialogHeader>
                                      <AlertDialogTitle>Delete course</AlertDialogTitle>
                                      <AlertDialogDescription>
                                        Permanently delete {course.name}? This cannot be undone. All
                                        associated data will be removed.
                                      </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                                      <AlertDialogAction
                                        variant="destructive"
                                        onClick={() => void handleDeleteCourse(course)}
                                      >
                                        Delete
                                      </AlertDialogAction>
                                    </AlertDialogFooter>
                                  </AlertDialogContent>
                                </AlertDialog>
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
          )}
        </TabsContent>

        {/* ── Assignment templates tab ── */}
        <TabsContent value="assignment-templates" className="space-y-4 pt-4">
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
              No archived assignment templates. Active assignment templates can be archived from
              their detail pages or using the table actions.
            </p>
          ) : (
            <div className="overflow-x-auto">
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
                    const isBusy = busyAssignmentTemplateId === template.id;
                    return (
                      <tr
                        key={template.id}
                        className="border-b border-border hover:bg-accent/30 transition-colors"
                      >
                        <td className="py-2 pr-4">{template.title}</td>
                        <td className="py-2 pr-4">{template.category ?? '-'}</td>
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
                                  onClick={() => void handleRestoreAssignmentTemplate(template)}
                                >
                                  {isBusy ? 'Restoring...' : 'Restore'}
                                </Button>
                                <AlertDialog>
                                  <AlertDialogTrigger asChild>
                                    <Button variant="destructive" size="xs" disabled={isBusy}>
                                      Delete
                                    </Button>
                                  </AlertDialogTrigger>
                                  <AlertDialogContent>
                                    <AlertDialogHeader>
                                      <AlertDialogTitle>Delete assignment template</AlertDialogTitle>
                                      <AlertDialogDescription>
                                        Permanently delete {template.title}? This cannot be
                                        undone.
                                      </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                                      <AlertDialogAction
                                        variant="destructive"
                                        onClick={() => void handleDeleteAssignmentTemplate(template)}
                                      >
                                        Delete
                                      </AlertDialogAction>
                                    </AlertDialogFooter>
                                  </AlertDialogContent>
                                </AlertDialog>
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
          )}
        </TabsContent>

        {/* ── Assignments tab ── */}
        <TabsContent value="assignments" className="space-y-4 pt-4">
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
              No archived assignments. Active assignments can be archived from their detail pages or
              using the table actions.
            </p>
          ) : (
            <div className="overflow-x-auto">
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
                    <th className="pb-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedAssignments().map((assignment, index) => {
                    const isArchived = assignment.status === 'ARCHIVED';
                    const isBusy = busyAssignmentId === assignment.id;
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
                                <AlertDialog>
                                  <AlertDialogTrigger asChild>
                                    <Button variant="destructive" size="xs" disabled={isBusy}>
                                      Delete
                                    </Button>
                                  </AlertDialogTrigger>
                                  <AlertDialogContent>
                                    <AlertDialogHeader>
                                      <AlertDialogTitle>Delete assignment</AlertDialogTitle>
                                      <AlertDialogDescription>
                                        Permanently delete {assignment.title}? This cannot be
                                        undone.
                                      </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                                      <AlertDialogAction
                                        variant="destructive"
                                        onClick={() => void handleDeleteAssignment(assignment)}
                                      >
                                        Delete
                                      </AlertDialogAction>
                                    </AlertDialogFooter>
                                  </AlertDialogContent>
                                </AlertDialog>
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
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
