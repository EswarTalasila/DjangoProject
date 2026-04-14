'use client';

import { Loader2 } from 'lucide-react';

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
import type { Assignment } from '@/lib/assignment-api';
import type { AssignmentTemplate } from '@/lib/assignment-template-api';
import { formatDate } from '@/lib/utils';

type PreviewMode = 'teacher' | 'student';

function formatPoints(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(2).replace(/\.?0+$/, '');
}

export type AssignmentMetadataPanelProps = {
  assignment: Assignment;
  assignmentTemplate: AssignmentTemplate | null;
  courseName: string;
  totalPoints: number;
  canMutate: boolean;
  canEditAssignment: boolean;
  titleInput: string;
  onTitleInputChange: (value: string) => void;
  openAtInput: string;
  onOpenAtInputChange: (value: string) => void;
  dueAtInput: string;
  onDueAtInputChange: (value: string) => void;
  previewMode: PreviewMode;
  onPreviewModeChange: (mode: PreviewMode) => void;
  isUpdating: boolean;
  isArchiving: boolean;
  isDeleting: boolean;
  onUpdate: () => void;
  onArchive: () => void;
  onDelete: () => void;
};

export default function AssignmentMetadataPanel({
  assignment,
  assignmentTemplate,
  courseName,
  totalPoints,
  canMutate,
  canEditAssignment,
  titleInput,
  onTitleInputChange,
  openAtInput,
  onOpenAtInputChange,
  dueAtInput,
  onDueAtInputChange,
  previewMode,
  onPreviewModeChange,
  isUpdating,
  isArchiving,
  isDeleting,
  onUpdate,
  onArchive,
  onDelete,
}: AssignmentMetadataPanelProps) {
  return (
    <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="rounded-sm border border-border bg-card p-6 space-y-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground">
              {assignment.title || 'Untitled Assignment'}
            </h1>
            <p className="text-muted-foreground mt-1">
              {(assignmentTemplate?.title ?? assignment.assignmentTemplateTitle ?? 'Template unavailable')} • {courseName}
            </p>
          </div>
          <span className="bg-muted text-muted-foreground px-2 py-0.5 rounded text-xs font-medium shrink-0">
            {assignment.status}
          </span>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Assignment Template</p>
            <p className="text-sm text-foreground">
              {assignmentTemplate?.title ?? assignment.assignmentTemplateTitle ?? '-'}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Course</p>
            <p className="text-sm text-foreground">{courseName}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Questions</p>
            <p className="text-sm text-foreground">{assignmentTemplate?.questions.length ?? 0}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Total Points</p>
            <p className="text-sm text-foreground">{formatPoints(totalPoints)}</p>
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

          <div className="space-y-2">
            <Label htmlFor="assignment-title">Assignment Title</Label>
            <Input
              id="assignment-title"
              value={titleInput}
              onChange={(event) => onTitleInputChange(event.target.value)}
              disabled={!canEditAssignment || isUpdating}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="open-at">Open At</Label>
              <Input
                id="open-at"
                type="datetime-local"
                value={openAtInput}
                onChange={(event) => onOpenAtInputChange(event.target.value)}
                disabled={!canEditAssignment || isUpdating}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="due-at">Due At</Label>
              <Input
                id="due-at"
                type="datetime-local"
                value={dueAtInput}
                onChange={(event) => onDueAtInputChange(event.target.value)}
                disabled={!canEditAssignment || isUpdating}
              />
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Preview Mode</p>
            <div className="rounded border border-border p-1 inline-flex items-center gap-1 bg-card">
              <Button
                type="button"
                size="sm"
                variant={previewMode === 'teacher' ? 'default' : 'ghost'}
                onClick={() => onPreviewModeChange('teacher')}
              >
                Teacher View
              </Button>
              <Button
                type="button"
                size="sm"
                variant={previewMode === 'student' ? 'default' : 'ghost'}
                onClick={() => onPreviewModeChange('student')}
              >
                Student View
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <Button onClick={onUpdate} disabled={!canEditAssignment || isUpdating}>
              {isUpdating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Changes
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
                    Archiving hides this assignment from student active lists. This can't be undone yet.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={isArchiving}>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={(event) => {
                      event.preventDefault();
                      onArchive();
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
                      onDelete();
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
    </section>
  );
}
