'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Pencil, Plus, Search, Trash2 } from 'lucide-react';
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  deleteAssessment,
  listAssessments,
  type Assessment,
} from '@/lib/assessment-api';

type ApiError = { response?: { data?: { detail?: string } } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

type AssessmentListViewProps = {
  canManage: boolean;
};

export default function AssessmentListView({ canManage }: AssessmentListViewProps) {
  const router = useRouter();

  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadAssessments = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await listAssessments();
      setAssessments(data);
    } catch {
      setLoadError('Failed to load assessments.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    setIsLoading(true);
    void loadAssessments();
  }, [loadAssessments]);

  const filteredAssessments = useMemo(() => {
    if (!searchQuery.trim()) return assessments;
    const query = searchQuery.toLowerCase();
    return assessments.filter((a) => a.title.toLowerCase().includes(query));
  }, [assessments, searchQuery]);

  async function handleDelete() {
    if (deleteTargetId === null) return;

    setIsDeleting(true);
    try {
      await deleteAssessment(deleteTargetId);
      toast.success('Assessment deleted.');
      setDeleteTargetId(null);
      await loadAssessments();
    } catch (error: unknown) {
      const detail = extractDetail(error, '');
      if (
        (error as ApiError).response?.data?.detail?.toLowerCase().includes('referenced') ||
        (error as { response?: { status?: number } }).response?.status === 409
      ) {
        toast.error('Cannot delete — assessment is referenced by assignments.');
      } else {
        toast.error(detail || 'Failed to delete assessment.');
      }
    } finally {
      setIsDeleting(false);
    }
  }

  function handleRowClick(id: number) {
    router.push(`/dashboard/assessments/${id}`);
  }

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            Assessments
          </h1>
          <p className="text-muted-foreground mt-1">
            {canManage
              ? 'Manage assessments and their questions.'
              : 'View assessments and their questions.'}
          </p>
        </div>
        {canManage && (
          <Button onClick={() => router.push('/dashboard/assessments/new')}>
            <Plus className="mr-2 h-4 w-4" />
            Create Assessment
          </Button>
        )}
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search assessments..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Error state */}
      {loadError && (
        <p className="text-sm text-destructive">{loadError}</p>
      )}

      {/* Loading state */}
      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading assessments...</p>
      )}

      {/* Empty state */}
      {!isLoading && !loadError && filteredAssessments.length === 0 && (
        <div className="rounded-sm border border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            {assessments.length === 0
              ? 'No assessments yet.'
              : 'No assessments match your search.'}
          </p>
        </div>
      )}

      {/* Assessment table */}
      {!isLoading && !loadError && filteredAssessments.length > 0 && (
        <div className="rounded-sm border border-border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted border-b border-border">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Title
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Category
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Grading Mode
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Scoring
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Questions
                </TableHead>
                {canManage && (
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground text-right">
                    Actions
                  </TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAssessments.map((assessment) => (
                <TableRow
                  key={assessment.id}
                  className="even:bg-muted/50 hover:bg-accent transition-colors cursor-pointer"
                  onClick={() => {
                    // Avoid accidental row navigation while a delete dialog/action is active.
                    if (deleteTargetId !== null || isDeleting) return;
                    handleRowClick(assessment.id);
                  }}
                >
                  <TableCell className="font-medium text-sm text-foreground">
                    {assessment.title}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {assessment.category ?? '-'}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {assessment.gradingMode}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {assessment.scoringPolicy}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {assessment.questions.length}
                  </TableCell>
                  {canManage && (
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={(e) => {
                            e.stopPropagation();
                            router.push(`/dashboard/assessments/${assessment.id}/edit`);
                          }}
                        >
                          <Pencil className="h-4 w-4" />
                          <span className="sr-only">Edit</span>
                        </Button>
                        <AlertDialog
                          open={deleteTargetId === assessment.id}
                          onOpenChange={(open) => {
                            if (!open) setDeleteTargetId(null);
                          }}
                        >
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-destructive hover:text-destructive"
                              onClick={(e) => {
                                e.stopPropagation();
                                setDeleteTargetId(assessment.id);
                              }}
                            >
                              <Trash2 className="h-4 w-4" />
                              <span className="sr-only">Delete</span>
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete Assessment</AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to delete &quot;{assessment.title}&quot;?
                                This action cannot be undone.
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
                                  e.stopPropagation();
                                  void handleDelete();
                                }}
                              >
                                {isDeleting ? 'Deleting...' : 'Delete'}
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
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
