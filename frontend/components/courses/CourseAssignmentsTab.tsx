'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus } from 'lucide-react';

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
  listAssignmentsByCourse,
  listAssignmentsForUser,
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

  const canCreate = userRole === 'TEACHER';

  const loadAssignments = useCallback(async () => {
    setLoadError(null);
    try {
      const items =
        userRole === 'STUDENT'
          ? await listAssignmentsForUser(userId).then((all) =>
              all.filter((assignment) => assignment.courseId === courseId),
            )
          : await listAssignmentsByCourse(courseId);
      setAssignments(items);
    } catch (error: unknown) {
      setLoadError(
        toErrorMessage(error, 'Failed to load assignments for this course.'),
      );
    } finally {
      setIsLoading(false);
    }
  }, [courseId, userId, userRole]);

  useEffect(() => {
    setIsLoading(true);
    void loadAssignments();
  }, [loadAssignments]);

  const sortedAssignments = useMemo(() => {
    return [...assignments].sort((a, b) => {
      const aOpen = a.openAt ? new Date(a.openAt).getTime() : 0;
      const bOpen = b.openAt ? new Date(b.openAt).getTime() : 0;
      return bOpen - aOpen;
    });
  }, [assignments]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-foreground">Course Assignments</h2>
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
                    {assignment.assessmentTitle ?? 'Template unavailable'}
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
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
