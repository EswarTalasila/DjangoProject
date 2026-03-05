'use client';

import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
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
import { listAssessments, type Assessment } from '@/lib/assessment-api';
import { listAssignmentsByCourse, type Assignment } from '@/lib/assignment-api';
import {
  archiveCourse,
  restoreCourse,
  purgeCourse,
  archiveAssessment,
  restoreAssessment,
  purgeAssessment,
  archiveAssignment,
  restoreAssignment,
  purgeAssignment,
} from '@/lib/lifecycle-api';
import { toErrorMessage } from '@/lib/utils';

// ── Props ──

type DataArchivesTabProps = {
  role: 'RESEARCHER' | 'ADMIN';
};

// ── Component ──

// eslint-disable-next-line @typescript-eslint/no-unused-vars -- reserved for admin-only purge gating
export default function DataArchivesTab({ role }: DataArchivesTabProps) {
  // -- Courses state --
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [showArchivedCourses, setShowArchivedCourses] = useState(false);
  const [busyCourseId, setBusyCourseId] = useState<number | null>(null);

  // -- Assessments state --
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loadingAssessments, setLoadingAssessments] = useState(true);
  const [showArchivedAssessments, setShowArchivedAssessments] = useState(false);
  const [busyAssessmentId, setBusyAssessmentId] = useState<number | null>(null);

  // -- Assignments state --
  const [assignments, setAssignments] = useState<(Assignment & { courseName?: string })[]>([]);
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [showArchivedAssignments, setShowArchivedAssignments] = useState(false);
  const [busyAssignmentId, setBusyAssignmentId] = useState<number | null>(null);

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

  const loadAssessments = useCallback(async () => {
    setLoadingAssessments(true);
    try {
      const data = await listAssessments();
      setAssessments(data);
    } catch {
      toast.error('Failed to load assessments.');
    } finally {
      setLoadingAssessments(false);
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

  // Load assessments on mount
  useEffect(() => {
    void loadAssessments();
  }, [loadAssessments]);

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

  // ── Filtered data ──

  const displayedCourses = courses;

  const displayedAssessments = showArchivedAssessments
    ? assessments
    : assessments.filter((a) => (a.status ?? 'ACTIVE') === 'ACTIVE');

  const displayedAssignments = showArchivedAssignments
    ? assignments
    : assignments.filter((a) => a.status === 'ACTIVE');

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

  // ── Assessment actions ──

  async function handleArchiveAssessment(assessment: Assessment) {
    setBusyAssessmentId(assessment.id);
    try {
      await archiveAssessment(assessment.id);
      toast.success('Assessment archived.');
      await loadAssessments();
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssessmentId(null);
    }
  }

  async function handleRestoreAssessment(assessment: Assessment) {
    setBusyAssessmentId(assessment.id);
    try {
      await restoreAssessment(assessment.id);
      toast.success('Assessment restored.');
      await loadAssessments();
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssessmentId(null);
    }
  }

  async function handleDeleteAssessment(assessment: Assessment) {
    setBusyAssessmentId(assessment.id);
    try {
      await purgeAssessment(assessment.id);
      toast.success('Assessment deleted.');
      await loadAssessments();
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setBusyAssessmentId(null);
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
    <div className="space-y-6">
      {/* ── Section 1: Courses ── */}
      <section className="rounded-sm border border-border bg-card p-4 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-lg font-semibold text-foreground">Courses</h2>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <Checkbox
              checked={showArchivedCourses}
              onCheckedChange={(checked) => setShowArchivedCourses(checked === true)}
            />
            Show archived courses
          </label>
        </div>

        {loadingCourses ? (
          <p className="text-sm text-muted-foreground">Loading courses...</p>
        ) : displayedCourses.length === 0 ? (
          <p className="text-sm text-muted-foreground">No courses found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">Name</th>
                  <th className="pb-2 pr-4 font-medium">Teacher</th>
                  <th className="pb-2 pr-4 font-medium">Students</th>
                  <th className="pb-2 pr-4 font-medium">Status</th>
                  <th className="pb-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {displayedCourses.map((course) => {
                  const isArchived = course.status === 'ARCHIVED';
                  const isBusy = busyCourseId === course.id;
                  return (
                    <tr key={course.id} className="border-b border-border">
                      <td className="py-2 pr-4">{course.name}</td>
                      <td className="py-2 pr-4">{course.teacherName ?? '-'}</td>
                      <td className="py-2 pr-4">{course.studentCount}</td>
                      <td className="py-2 pr-4">
                        {isArchived ? (
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800/40 dark:text-gray-400">
                            Archived
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                            Active
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
                                    Archive {course.name}? This will also archive all assignments in
                                    this course. Students will no longer be able to submit work.
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
      </section>

      {/* ── Section 2: Assessments ── */}
      <section className="rounded-sm border border-border bg-card p-4 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-lg font-semibold text-foreground">Assessments</h2>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <Checkbox
              checked={showArchivedAssessments}
              onCheckedChange={(checked) => setShowArchivedAssessments(checked === true)}
            />
            Show archived assessments
          </label>
        </div>

        {loadingAssessments ? (
          <p className="text-sm text-muted-foreground">Loading assessments...</p>
        ) : displayedAssessments.length === 0 ? (
          <p className="text-sm text-muted-foreground">No assessments found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">Title</th>
                  <th className="pb-2 pr-4 font-medium">Category</th>
                  <th className="pb-2 pr-4 font-medium">Status</th>
                  <th className="pb-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {displayedAssessments.map((assessment) => {
                  const status = assessment.status ?? 'ACTIVE';
                  const isArchived = status === 'ARCHIVED';
                  const isBusy = busyAssessmentId === assessment.id;
                  return (
                    <tr key={assessment.id} className="border-b border-border">
                      <td className="py-2 pr-4">{assessment.title}</td>
                      <td className="py-2 pr-4">{assessment.category ?? '-'}</td>
                      <td className="py-2 pr-4">
                        {isArchived ? (
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800/40 dark:text-gray-400">
                            Archived
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                            Active
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
                                onClick={() => void handleRestoreAssessment(assessment)}
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
                                    <AlertDialogTitle>Delete assessment</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Permanently delete {assessment.title}? This cannot be undone.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                      variant="destructive"
                                      onClick={() => void handleDeleteAssessment(assessment)}
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
                                  <AlertDialogTitle>Archive assessment</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Archive {assessment.title}? It will no longer appear in active
                                    views.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => void handleArchiveAssessment(assessment)}
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
      </section>

      {/* ── Section 3: Assignments ── */}
      <section className="rounded-sm border border-border bg-card p-4 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-lg font-semibold text-foreground">Assignments</h2>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <Checkbox
              checked={showArchivedAssignments}
              onCheckedChange={(checked) => setShowArchivedAssignments(checked === true)}
            />
            Show archived assignments
          </label>
        </div>

        {loadingAssignments ? (
          <p className="text-sm text-muted-foreground">Loading assignments...</p>
        ) : displayedAssignments.length === 0 ? (
          <p className="text-sm text-muted-foreground">No assignments found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">Title</th>
                  <th className="pb-2 pr-4 font-medium">Course</th>
                  <th className="pb-2 pr-4 font-medium">Due Date</th>
                  <th className="pb-2 pr-4 font-medium">Status</th>
                  <th className="pb-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {displayedAssignments.map((assignment) => {
                  const isArchived = assignment.status === 'ARCHIVED';
                  const isBusy = busyAssignmentId === assignment.id;
                  return (
                    <tr key={assignment.id} className="border-b border-border">
                      <td className="py-2 pr-4">{assignment.title}</td>
                      <td className="py-2 pr-4">{assignment.courseName ?? '-'}</td>
                      <td className="py-2 pr-4">
                        {assignment.dueAt
                          ? new Date(assignment.dueAt).toLocaleDateString()
                          : '-'}
                      </td>
                      <td className="py-2 pr-4">
                        {isArchived ? (
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800/40 dark:text-gray-400">
                            Archived
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                            Active
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
                                      Permanently delete {assignment.title}? This cannot be undone.
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
      </section>
    </div>
  );
}
