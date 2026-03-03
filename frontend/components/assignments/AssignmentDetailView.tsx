'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Loader2 } from 'lucide-react';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  archiveAssignment,
  deleteAssignment,
  getAssignment,
  updateAssignment,
  type Assignment,
} from '@/lib/assignment-api';
import { listAssessments } from '@/lib/assessment-api';
import { listCourses } from '@/lib/course-api';

type ApiError = { response?: { data?: { detail?: string }; status?: number } };

type AssignmentDetailViewProps = {
  assignmentId: number;
  canMutate: boolean;
};

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

function toLocalInputValue(value: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toIsoOrNull(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function formatDate(value: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

export default function AssignmentDetailView({ assignmentId, canMutate }: AssignmentDetailViewProps) {
  const router = useRouter();

  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [assessmentTitle, setAssessmentTitle] = useState<string>('');
  const [courseName, setCourseName] = useState<string>('');
  const [openAtInput, setOpenAtInput] = useState('');
  const [dueAtInput, setDueAtInput] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const [item, assessments, courses] = await Promise.all([
        getAssignment(assignmentId),
        listAssessments().catch(() => []),
        listCourses().catch(() => []),
      ]);
      setAssignment(item);
      setOpenAtInput(toLocalInputValue(item.openAt));
      setDueAtInput(toLocalInputValue(item.dueAt));

      const aTitle = assessments.find((a) => a.id === item.assessmentId)?.title;
      const cName = courses.find((c) => c.id === item.courseId)?.name;
      setAssessmentTitle(aTitle ?? `Assessment #${item.assessmentId}`);
      setCourseName(cName ?? (item.courseId ? `Course #${item.courseId}` : '-'));
    } catch {
      setLoadError('Failed to load assignment.');
    } finally {
      setIsLoading(false);
    }
  }, [assignmentId]);

  useEffect(() => {
    setIsLoading(true);
    void load();
  }, [load]);

  const canEditSchedule = useMemo(() => {
    return canMutate && assignment?.status === 'ACTIVE';
  }, [assignment?.status, canMutate]);

  async function handleUpdateSchedule() {
    if (!assignment) return;

    const openIso = toIsoOrNull(openAtInput);
    const dueIso = toIsoOrNull(dueAtInput);

    if (!openIso) {
      toast.error('Please provide a valid open date/time.');
      return;
    }
    if (dueIso && openIso >= dueIso) {
      toast.error('Open time must be before due time.');
      return;
    }

    setIsUpdating(true);
    try {
      const updated = await updateAssignment(assignment.id, {
        openAt: openIso,
        dueAt: dueIso,
      });
      setAssignment(updated);
      setOpenAtInput(toLocalInputValue(updated.openAt));
      setDueAtInput(toLocalInputValue(updated.dueAt));
      toast.success('Assignment schedule updated.');
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to update assignment.'));
    } finally {
      setIsUpdating(false);
    }
  }

  async function handleArchive() {
    if (!assignment) return;

    setIsArchiving(true);
    try {
      const updated = await archiveAssignment(assignment.id);
      setAssignment(updated);
      toast.success('Assignment archived.');
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to archive assignment.'));
    } finally {
      setIsArchiving(false);
    }
  }

  async function handleDelete() {
    if (!assignment) return;

    setIsDeleting(true);
    try {
      await deleteAssignment(assignment.id);
      toast.success('Assignment deleted.');
      router.push('/dashboard/assignments');
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to delete assignment.'));
    } finally {
      setIsDeleting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (loadError || !assignment) {
    return (
      <div className="space-y-6 p-6 max-w-5xl mx-auto">
        <Link
          href="/dashboard/assignments"
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Assignments
        </Link>
        <p className="text-sm text-destructive">{loadError ?? 'Assignment not found.'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      <Link
        href="/dashboard/assignments"
        className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Assignments
      </Link>

      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Assignment #{assignment.id}</h1>
          <p className="text-muted-foreground mt-1">
            {assessmentTitle} • {courseName}
          </p>
        </div>
        <span className="bg-muted text-muted-foreground px-2 py-0.5 rounded text-xs font-medium">
          {assignment.status}
        </span>
      </div>

      <div className="rounded-sm border border-border bg-card p-6 space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Assessment</p>
            <p className="text-sm text-foreground">{assessmentTitle}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Course</p>
            <p className="text-sm text-foreground">{courseName}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Open At</p>
            <p className="text-sm text-foreground">{formatDate(assignment.openAt)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Due At</p>
            <p className="text-sm text-foreground">{formatDate(assignment.dueAt)}</p>
          </div>
        </div>
      </div>

      {canMutate && (
        <div className="rounded-sm border border-border bg-card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-foreground">Manage Assignment</h2>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="open-at">Open At</Label>
              <Input
                id="open-at"
                type="datetime-local"
                value={openAtInput}
                onChange={(event) => setOpenAtInput(event.target.value)}
                disabled={!canEditSchedule || isUpdating}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="due-at">Due At</Label>
              <Input
                id="due-at"
                type="datetime-local"
                value={dueAtInput}
                onChange={(event) => setDueAtInput(event.target.value)}
                disabled={!canEditSchedule || isUpdating}
              />
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <Button onClick={() => void handleUpdateSchedule()} disabled={!canEditSchedule || isUpdating}>
              {isUpdating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Schedule
            </Button>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" disabled={assignment.status === 'ARCHIVED' || isArchiving}>
                  {isArchiving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Archive
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Archive Assignment</AlertDialogTitle>
                  <AlertDialogDescription>
                    Archiving hides this assignment from student active lists. This can’t be undone yet.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={isArchiving}>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={(event) => {
                      event.preventDefault();
                      void handleArchive();
                    }}
                    disabled={isArchiving}
                  >
                    Confirm Archive
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" disabled={isDeleting}>
                  {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Delete
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete Assignment</AlertDialogTitle>
                  <AlertDialogDescription>
                    Delete is blocked if submissions progressed beyond NOT_STARTED.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    variant="destructive"
                    onClick={(event) => {
                      event.preventDefault();
                      void handleDelete();
                    }}
                    disabled={isDeleting}
                  >
                    Confirm Delete
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      )}
    </div>
  );
}
