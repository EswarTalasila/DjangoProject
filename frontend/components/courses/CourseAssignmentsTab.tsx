'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Archive, Plus, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  archiveAssignment,
  listAssignmentsByCourse,
  listAssignmentsForUser,
  restoreAssignment,
  type Assignment,
} from '@/lib/assignment-api';
import { toErrorMessage, formatDate } from '@/lib/utils';

type CourseAssignmentsTabProps = {
  courseId: number;
  userRole: 'TEACHER' | 'RESEARCHER' | 'STUDENT';
  userId: number;
};

export default function CourseAssignmentsTab({
  courseId,
  userRole,
  userId,
}: CourseAssignmentsTabProps) {
  const router = useRouter();
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const [busyAssignmentId, setBusyAssignmentId] = useState<number | null>(null);

  const canCreate = userRole === 'TEACHER';
  const canManageLifecycle = userRole === 'TEACHER';

  const loadAssignments = useCallback(async () => {
    setLoadError(null);
    try {
      const items =
        userRole === 'STUDENT'
          ? await listAssignmentsForUser(userId).then((all) =>
              all.filter((assignment) => assignment.courseId === courseId),
            )
          : await listAssignmentsByCourse(
              courseId,
              showArchived ? { includeArchived: true } : undefined,
            );
      setAssignments(items);
    } catch (error: unknown) {
      setLoadError(
        toErrorMessage(error, 'Failed to load assignments for this course.'),
      );
    } finally {
      setIsLoading(false);
    }
  }, [courseId, showArchived, userId, userRole]);

  useEffect(() => {
    setIsLoading(true);
    void loadAssignments();
  }, [loadAssignments]);

  const sortedAssignments = useMemo(() => {
    return [...assignments].sort((a, b) => {
      const aArchived = a.status === 'ARCHIVED' ? 1 : 0;
      const bArchived = b.status === 'ARCHIVED' ? 1 : 0;
      if (aArchived !== bArchived) {
        return aArchived - bArchived;
      }
      const aOpen = a.openAt ? new Date(a.openAt).getTime() : 0;
      const bOpen = b.openAt ? new Date(b.openAt).getTime() : 0;
      return bOpen - aOpen;
    });
  }, [assignments]);

  async function handleArchive(assignmentId: number) {
    setBusyAssignmentId(assignmentId);
    try {
      await archiveAssignment(assignmentId);
      toast.success('Assignment archived.');
      await loadAssignments();
    } catch (error: unknown) {
      const message = toErrorMessage(error, 'Failed to archive assignment.');
      setLoadError(message);
      toast.error(message);
    } finally {
      setBusyAssignmentId(null);
    }
  }

  async function handleRestore(assignmentId: number) {
    setBusyAssignmentId(assignmentId);
    try {
      await restoreAssignment(assignmentId);
      toast.success('Assignment restored.');
      await loadAssignments();
    } catch (error: unknown) {
      const message = toErrorMessage(error, 'Failed to restore assignment.');
      setLoadError(message);
      toast.error(message);
    } finally {
      setBusyAssignmentId(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-foreground">Course Assignments</h2>
        <div className="flex items-center gap-3">
          {userRole !== 'STUDENT' && (
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={showArchived}
                onCheckedChange={(checked) => setShowArchived(checked === true)}
              />
              Show archived
            </label>
          )}
          {canCreate && (
            <Button
              onClick={() =>
                router.push(`/dashboard/assignments/new?courseId=${courseId}`)
              }
            >
              <Plus className="mr-2 h-4 w-4" />
              Create Assignment
            </Button>
          )}
        </div>
      </div>

      {loadError && <p className="text-sm text-destructive">{loadError}</p>}

      {isLoading && (
        <div className="rounded-sm border border-border bg-card p-8">
          <p className="text-sm text-muted-foreground">Loading assignments...</p>
        </div>
      )}

      {!isLoading && !loadError && sortedAssignments.length === 0 && (
        <div className="rounded-sm border border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">No assignments for this course yet.</p>
        </div>
      )}

      {!isLoading && !loadError && sortedAssignments.length > 0 && (
        <div className="rounded-sm border border-border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted border-b border-border">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Assignment
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Template
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Status
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Opens
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Due
                </TableHead>
                {canManageLifecycle && (
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Actions
                  </TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedAssignments.map((assignment) => (
                <TableRow
                  key={assignment.id}
                  className="even:bg-muted/50 hover:bg-accent transition-colors cursor-pointer"
                  onClick={() =>
                    router.push(`/dashboard/assignments/${assignment.id}`)
                  }
                >
                  <TableCell className="font-medium text-sm text-foreground">
                    {assignment.title}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {assignment.assignmentTemplateTitle ?? 'Assignment template unavailable'}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {assignment.status}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(assignment.openAt)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(assignment.dueAt)}
                  </TableCell>
                  {canManageLifecycle && (
                    <TableCell
                      className="text-sm text-muted-foreground"
                      onClick={(event) => event.stopPropagation()}
                    >
                      {assignment.status === 'ARCHIVED' ? (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busyAssignmentId === assignment.id}
                          onClick={() => void handleRestore(assignment.id)}
                        >
                          <RotateCcw className="mr-2 h-4 w-4" />
                          Restore
                        </Button>
                      ) : (
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={busyAssignmentId === assignment.id}
                          onClick={() => void handleArchive(assignment.id)}
                        >
                          <Archive className="mr-2 h-4 w-4" />
                          Archive
                        </Button>
                      )}
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
