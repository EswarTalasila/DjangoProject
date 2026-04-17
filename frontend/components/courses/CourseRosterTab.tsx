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
import { toErrorMessage, formatShortDate } from '@/lib/utils';

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
      toast.error(toErrorMessage(error, 'Failed to remove student.'));
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
      toast.error(toErrorMessage(error, 'Failed to issue reset code.'));
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
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground text-right">
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
                    {formatShortDate(student.enrolledAt)}
                  </TableCell>
                  {canManage && (
                    <TableCell className="space-x-2 text-right">
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
