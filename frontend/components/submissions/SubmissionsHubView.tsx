'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  listAssignmentSubmissions,
  listMySubmissions,
  type SubmissionCompactDTO,
  type SubmissionStatus,
} from '@/lib/submission-api';
import { StatusBadge } from '@/components/ui/status-badge';
import {
  listAssignmentsByCourse,
  listAssignmentsForUser,
  type Assignment,
} from '@/lib/assignment-api';
import { listCourses, type CourseSummary } from '@/lib/course-api';
import { toErrorMessage, formatDate, formatScore } from '@/lib/utils';

type Role = 'ADMIN' | 'TEACHER' | 'RESEARCHER' | 'STUDENT';

type SubmissionsHubViewProps = {
  role: Role;
  userId: number;
};

const STATUS_OPTIONS: Array<{ value: 'ALL' | SubmissionStatus; label: string }> = [
  { value: 'ALL', label: 'All statuses' },
  { value: 'NOT_STARTED', label: 'Not Started' },
  { value: 'IN_PROGRESS', label: 'Draft' },
  { value: 'SUBMITTED', label: 'Submitted' },
  { value: 'GRADED', label: 'Graded' },
];

function displayStatus(s: string): string {
  if (s === 'IN_PROGRESS' || s === 'NOT_STARTED') return 'Not Submitted';
  if (s === 'SUBMITTED') return 'Submitted';
  if (s === 'GRADED') return 'Graded';
  return s;
}

function statusVariant(s: string): string {
  if (s === 'GRADED') return 'ACTIVE';
  if (s === 'SUBMITTED') return 'SUBMITTED';
  return 'NOT_STARTED';
}

export default function SubmissionsHubView({ role, userId }: SubmissionsHubViewProps) {
  const router = useRouter();

  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshingRows, setIsRefreshingRows] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [studentStatusFilter, setStudentStatusFilter] = useState<'ALL' | SubmissionStatus>('ALL');
  const [mySubmissions, setMySubmissions] = useState<SubmissionCompactDTO[]>([]);
  const [myAssignments, setMyAssignments] = useState<Record<number, string>>({});

  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>('');
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<string>('');
  const [submissionRows, setSubmissionRows] = useState<SubmissionCompactDTO[]>([]);

  const isStudent = role === 'STUDENT';
  const isTeacher = role === 'TEACHER';

  const loadStudentSubmissions = useCallback(async () => {
    setLoadError(null);
    try {
      const [submissions, assignmentList] = await Promise.all([
        listMySubmissions(studentStatusFilter === 'ALL' ? undefined : studentStatusFilter),
        listAssignmentsForUser(userId).catch(() => []),
      ]);
      const assignmentMap: Record<number, string> = {};
      for (const assignment of assignmentList) {
        assignmentMap[assignment.id] = assignment.title || `Assignment #${assignment.id}`;
      }
      setMyAssignments(assignmentMap);
      setMySubmissions(submissions);
    } catch (error: unknown) {
      setLoadError(toErrorMessage(error, 'Failed to load your submissions.'));
    }
  }, [studentStatusFilter, userId]);

  const loadRowsForAssignment = useCallback(async (assignmentId: number) => {
    setLoadError(null);
    setIsRefreshingRows(true);
    try {
      const rows = await listAssignmentSubmissions(assignmentId);
      setSubmissionRows(rows);
    } catch (error: unknown) {
      setLoadError(toErrorMessage(error, 'Failed to load submissions for this assignment.'));
      setSubmissionRows([]);
    } finally {
      setIsRefreshingRows(false);
    }
  }, []);

  const loadTeacherScope = useCallback(async () => {
    setLoadError(null);
    try {
      const list = await listAssignmentsForUser(userId);
      setAssignments(list);
      const nextAssignmentId = list[0] ? String(list[0].id) : '';
      setSelectedAssignmentId(nextAssignmentId);
      if (nextAssignmentId) {
        await loadRowsForAssignment(Number(nextAssignmentId));
      } else {
        setSubmissionRows([]);
      }
    } catch (error: unknown) {
      setLoadError(toErrorMessage(error, 'Failed to load your assignments.'));
    }
  }, [loadRowsForAssignment, userId]);

  const loadResearcherScope = useCallback(async () => {
    setLoadError(null);
    try {
      const courseList = await listCourses();
      setCourses(courseList);
      const nextCourseId = courseList[0] ? String(courseList[0].id) : '';
      setSelectedCourseId(nextCourseId);

      if (!nextCourseId) {
        setAssignments([]);
        setSelectedAssignmentId('');
        setSubmissionRows([]);
        return;
      }

      const assignmentList = await listAssignmentsByCourse(Number(nextCourseId));
      setAssignments(assignmentList);
      const nextAssignmentId = assignmentList[0] ? String(assignmentList[0].id) : '';
      setSelectedAssignmentId(nextAssignmentId);
      if (nextAssignmentId) {
        await loadRowsForAssignment(Number(nextAssignmentId));
      } else {
        setSubmissionRows([]);
      }
    } catch (error: unknown) {
      setLoadError(toErrorMessage(error, 'Failed to load submissions scope.'));
    }
  }, [loadRowsForAssignment]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      if (isStudent) {
        await loadStudentSubmissions();
      } else if (isTeacher) {
        await loadTeacherScope();
      } else {
        await loadResearcherScope();
      }
      if (!cancelled) {
        setIsLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [isStudent, isTeacher, loadResearcherScope, loadStudentSubmissions, loadTeacherScope]);

  async function handleCourseChange(value: string) {
    setSelectedCourseId(value);
    setSelectedAssignmentId('');
    setSubmissionRows([]);
    if (!value) {
      setAssignments([]);
      return;
    }
    setIsRefreshingRows(true);
    setLoadError(null);
    try {
      const list = await listAssignmentsByCourse(Number(value));
      setAssignments(list);
      const nextAssignmentId = list[0] ? String(list[0].id) : '';
      setSelectedAssignmentId(nextAssignmentId);
      if (nextAssignmentId) {
        await loadRowsForAssignment(Number(nextAssignmentId));
      }
    } catch (error: unknown) {
      setLoadError(toErrorMessage(error, 'Failed to load assignments for this course.'));
    } finally {
      setIsRefreshingRows(false);
    }
  }

  async function handleAssignmentChange(value: string) {
    setSelectedAssignmentId(value);
    setSubmissionRows([]);
    if (!value) return;
    await loadRowsForAssignment(Number(value));
  }

  const selectedAssignment = useMemo(() => {
    if (!selectedAssignmentId) return null;
    return assignments.find((assignment) => String(assignment.id) === selectedAssignmentId) ?? null;
  }, [assignments, selectedAssignmentId]);

  return (
    <div className="space-y-6 p-6 w-full max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          {isStudent ? 'My Submissions' : 'Submissions'}
        </h1>
        <p className="text-muted-foreground mt-1">
          {isStudent
            ? 'Track draft, submitted, and graded work.'
            : 'Review submissions by assignment and open full submission detail for grading.'}
        </p>
      </div>

      {loadError && <p className="text-sm text-destructive">{loadError}</p>}

      {isStudent ? (
        <div className="space-y-4">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="w-full max-w-xs">
              <Select
                value={studentStatusFilter}
                onValueChange={(next) => setStudentStatusFilter(next as 'ALL' | SubmissionStatus)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              type="button"
              variant="outline"
              onClick={() => void loadStudentSubmissions()}
              disabled={isLoading}
            >
              Refresh
            </Button>
          </div>

          {isLoading ? (
            <div className="rounded-sm border border-border bg-card p-8 text-sm text-muted-foreground">
              Loading submissions...
            </div>
          ) : mySubmissions.length === 0 ? (
            <div className="rounded-sm border border-border bg-card p-8 text-sm text-muted-foreground text-center">
              No submissions found for this filter.
            </div>
          ) : (
            <div className="rounded-sm border border-border bg-card overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted border-b border-border">
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Assignment
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Status
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Score
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Submitted
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground text-right">
                      Actions
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mySubmissions.map((submission) => (
                    <TableRow key={submission.id} className="even:bg-muted/50 hover:bg-accent transition-colors">
                      <TableCell className="font-medium text-sm text-foreground">
                        {myAssignments[submission.assignmentId] ?? `Assignment #${submission.assignmentId}`}
                      </TableCell>
                      <TableCell>
                        <StatusBadge
                          status={submission.status}
                          label={displayStatus(submission.status)}
                          className="text-[10px]"
                        />
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{formatScore(submission.score)}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(submission.submittedAt)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="inline-flex gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => router.push(`/dashboard/assignments/${submission.assignmentId}`)}
                          >
                            Open Assignment
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => router.push(`/dashboard/submissions/${submission.id}`)}
                          >
                            View Submission
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-3 flex-wrap">
            {!isTeacher && (
              <div className="w-full max-w-xs">
                <Select value={selectedCourseId} onValueChange={(next) => void handleCourseChange(next)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select course" />
                  </SelectTrigger>
                  <SelectContent>
                    {courses.map((course) => (
                      <SelectItem key={course.id} value={String(course.id)}>
                        {course.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="w-full max-w-sm">
              <Select value={selectedAssignmentId} onValueChange={(next) => void handleAssignmentChange(next)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select assignment" />
                </SelectTrigger>
                <SelectContent>
                  {assignments.map((assignment) => (
                    <SelectItem key={assignment.id} value={String(assignment.id)}>
                      {assignment.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              type="button"
              variant="outline"
              onClick={() => {
                if (selectedAssignmentId) {
                  void loadRowsForAssignment(Number(selectedAssignmentId));
                }
              }}
              disabled={isRefreshingRows || !selectedAssignmentId}
            >
              Refresh
            </Button>
          </div>

          {selectedAssignment && (
            <p className="text-sm text-muted-foreground">
              Showing submissions for <span className="text-foreground font-medium">{selectedAssignment.title}</span>
            </p>
          )}

          {isLoading || isRefreshingRows ? (
            <div className="rounded-sm border border-border bg-card p-8 text-sm text-muted-foreground flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading submissions...
            </div>
          ) : !selectedAssignmentId ? (
            <div className="rounded-sm border border-border bg-card p-8 text-sm text-muted-foreground text-center">
              Select an assignment to view submissions.
            </div>
          ) : submissionRows.length === 0 ? (
            <div className="rounded-sm border border-border bg-card p-8 text-sm text-muted-foreground text-center">
              No submissions found for this assignment.
            </div>
          ) : (
            <div className="rounded-sm border border-border bg-card overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted border-b border-border">
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Student
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Course
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Assignment
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Status
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Score
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Submitted
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground text-right">
                      Actions
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {submissionRows.map((submission) => (
                    <TableRow key={submission.id} className="even:bg-muted/50 hover:bg-accent transition-colors">
                      <TableCell className="font-medium text-sm text-foreground">
                        {submission.studentName ?? 'Unknown'}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {submission.courseName ?? '-'}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {submission.assignmentTitle ?? `Assignment #${submission.assignmentId}`}
                      </TableCell>
                      <TableCell>
                        <StatusBadge
                          status={statusVariant(submission.status)}
                          label={displayStatus(submission.status)}
                          className="text-[10px]"
                        />
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {submission.status === 'GRADED' ? formatScore(submission.score) : '-'}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(submission.submittedAt)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          type="button"
                          size="sm"
                          onClick={() => router.push(`/dashboard/submissions/${submission.id}`)}
                        >
                          {submission.status === 'SUBMITTED' ? 'Grade' : 'View'}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
