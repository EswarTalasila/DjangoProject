'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Archive, ArrowLeft, Loader2, Pencil, Trash2 } from 'lucide-react';
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
import {
  archiveRubric,
  deleteRubric,
  getRubric,
  type Rubric,
  type RubricCriterion,
} from '@/lib/rubric-api';
import { toErrorMessage } from '@/lib/utils';

type RubricDetailViewProps = {
  rubricId: number;
  canManage: boolean;
};

export default function RubricDetailView({
  rubricId,
  canManage,
}: RubricDetailViewProps) {
  const router = useRouter();

  const [rubric, setRubric] = useState<Rubric | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadRubric = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await getRubric(rubricId);
      setRubric(data);
    } catch {
      setLoadError('Failed to load rubric.');
    } finally {
      setIsLoading(false);
    }
  }, [rubricId]);

  useEffect(() => {
    setIsLoading(true);
    void loadRubric();
  }, [loadRubric]);

  async function handleDelete() {
    setIsDeleting(true);
    try {
      await deleteRubric(rubricId);
      toast.success('Rubric deleted.');
      router.push('/dashboard/rubrics');
    } catch (error: unknown) {
      const axErr = error as { response?: { data?: { detail?: string }; status?: number } };
      if (
        axErr.response?.data?.detail
          ?.toLowerCase()
          .includes('referenced') ||
        axErr.response?.status === 409
      ) {
        toast.error('Cannot delete — rubric is referenced by assessments.');
      } else {
        toast.error(toErrorMessage(error, 'Failed to delete rubric.'));
      }
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleArchive() {
    try {
      await archiveRubric(rubricId);
      toast.success('Rubric archived.');
      await loadRubric();
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to archive rubric.'));
    }
  }

  function statusBadgeClasses(status: string): string {
    if (status === 'ARCHIVED') {
      return 'bg-status-warning-bg text-foreground';
    }
    return 'bg-status-success-bg text-foreground';
  }

  // -- Loading state --
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // -- Load error state --
  if (loadError) {
    return (
      <div className="space-y-6 p-6 max-w-4xl mx-auto">
        <Link
          href="/dashboard/rubrics"
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Rubrics
        </Link>
        <p className="text-sm text-destructive">{loadError}</p>
      </div>
    );
  }

  // -- Not found state --
  if (!rubric) {
    return (
      <div className="space-y-6 p-6 max-w-4xl mx-auto">
        <Link
          href="/dashboard/rubrics"
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Rubrics
        </Link>
        <p className="text-sm text-muted-foreground">Rubric not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-4xl mx-auto">
      {/* Back link */}
      <Link
        href="/dashboard/rubrics"
        className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Rubrics
      </Link>

      {/* Header row */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          {rubric.title}
        </h1>
        <span
          className={`px-2 py-0.5 rounded text-xs font-medium ${statusBadgeClasses(rubric.status)}`}
        >
          {rubric.status}
        </span>

        {canManage && (
          <div className="ml-auto flex items-center gap-2">
            {rubric.status === 'ACTIVE' && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => void handleArchive()}
                title="Archive"
              >
                <Archive className="h-4 w-4" />
                <span className="sr-only">Archive</span>
              </Button>
            )}

            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() =>
                router.push(`/dashboard/rubrics/${rubricId}/edit`)
              }
            >
              <Pencil className="h-4 w-4" />
              <span className="sr-only">Edit</span>
            </Button>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                  <span className="sr-only">Delete</span>
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete Rubric</AlertDialogTitle>
                  <AlertDialogDescription>
                    Are you sure you want to delete this rubric? This action
                    cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={isDeleting}>
                    Cancel
                  </AlertDialogCancel>
                  <AlertDialogAction
                    variant="destructive"
                    disabled={isDeleting}
                    onClick={(e) => {
                      e.preventDefault();
                      void handleDelete();
                    }}
                  >
                    {isDeleting ? 'Deleting...' : 'Delete'}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}
      </div>

      {/* Description */}
      {rubric.description && (
        <p className="text-sm text-muted-foreground">{rubric.description}</p>
      )}

      {/* Criteria section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-foreground">
          Criteria ({rubric.criteria.length})
        </h2>

        {rubric.criteria.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No criteria defined in this rubric.
          </p>
        )}

        {rubric.criteria.map((criterion, index) => (
          <CriterionCard key={criterion.id} criterion={criterion} index={index} />
        ))}
      </div>
    </div>
  );
}

// -- Criterion Card --

function CriterionCard({
  criterion,
  index,
}: {
  criterion: RubricCriterion;
  index: number;
}) {
  return (
    <div className="rounded-sm border border-border bg-card p-4 space-y-3">
      {/* Criterion header */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm font-semibold text-foreground">
          Criterion {index + 1}
        </span>
        <span className="text-sm font-medium text-foreground">
          {criterion.title}
        </span>
        <span className="text-sm text-muted-foreground">
          Weight: {criterion.weight}
        </span>
      </div>

      {/* Description */}
      {criterion.description && (
        <p className="text-sm text-muted-foreground">{criterion.description}</p>
      )}

      {/* Levels table */}
      {criterion.levels.length > 0 && (
        <div className="rounded-sm border border-border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted border-b border-border">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Label
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Points
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Description
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {criterion.levels.map((level) => (
                <TableRow key={level.id} className="even:bg-muted/50">
                  <TableCell className="text-sm font-medium text-foreground">
                    {level.label}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {level.points}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {level.description || '-'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {criterion.levels.length === 0 && (
        <p className="text-sm text-muted-foreground">No levels defined.</p>
      )}
    </div>
  );
}
