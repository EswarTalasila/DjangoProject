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
  deleteAssignmentTemplate,
  listAssignmentTemplates,
  type AssignmentTemplate,
} from '@/lib/assignment-template-api';
import { StatusBadge } from '@/components/ui/status-badge';
import { toErrorMessage } from '@/lib/utils';

type AssignmentTemplateListViewProps = {
  canManage: boolean;
};

export default function AssignmentTemplateListView({ canManage }: AssignmentTemplateListViewProps) {
  const router = useRouter();

  const [assignmentTemplates, setAssignmentTemplates] = useState<AssignmentTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadAssignmentTemplates = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await listAssignmentTemplates();
      setAssignmentTemplates(data);
    } catch {
      setLoadError('Failed to load assignment templates.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    setIsLoading(true);
    void loadAssignmentTemplates();
  }, [loadAssignmentTemplates]);

  const filteredAssignmentTemplates = useMemo(() => {
    if (!searchQuery.trim()) return assignmentTemplates;
    const query = searchQuery.toLowerCase();
    return assignmentTemplates.filter((a) => a.title.toLowerCase().includes(query));
  }, [assignmentTemplates, searchQuery]);

  async function handleDelete() {
    if (deleteTargetId === null) return;

    setIsDeleting(true);
    try {
      await deleteAssignmentTemplate(deleteTargetId);
      toast.success('Assignment template deleted.');
      setDeleteTargetId(null);
      await loadAssignmentTemplates();
    } catch (error: unknown) {
      const axErr = error as { response?: { data?: { detail?: string }; status?: number } };
      if (
        axErr.response?.data?.detail?.toLowerCase().includes('referenced') ||
        axErr.response?.status === 409
      ) {
        toast.error(describeDeleteConflict(axErr.response?.data?.detail));
      } else {
        toast.error(toErrorMessage(error, 'Failed to delete assignment template.'));
      }
    } finally {
      setIsDeleting(false);
    }
  }

  function handleRowClick(id: number) {
    router.push(`/dashboard/assignment-templates/${id}`);
  }

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            Assignment Templates
          </h1>
          <p className="text-muted-foreground mt-1">
            {canManage
              ? 'Manage assignment templates and their questions.'
              : 'View assignment templates and their questions.'}
          </p>
        </div>
        {canManage && (
          <Button onClick={() => router.push('/dashboard/assignment-templates/new')}>
            <Plus className="mr-2 h-4 w-4" />
            Create Assignment Template
          </Button>
        )}
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search assignment templates..."
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
        <p className="text-sm text-muted-foreground">Loading assignment templates...</p>
      )}

      {/* Empty state */}
      {!isLoading && !loadError && filteredAssignmentTemplates.length === 0 && (
        <div className="rounded-sm border border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            {assignmentTemplates.length === 0
              ? 'No assignment templates yet.'
              : 'No assignment templates match your search.'}
          </p>
        </div>
      )}

      {/* Assignment template table */}
      {!isLoading && !loadError && filteredAssignmentTemplates.length > 0 && (
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
                  Status
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
              {filteredAssignmentTemplates.map((assignmentTemplate) => (
                <TableRow
                  key={assignmentTemplate.id}
                  className="even:bg-muted/50 hover:bg-accent transition-colors cursor-pointer"
                  onClick={() => {
                    // Avoid accidental row navigation while a delete dialog/action is active.
                    if (deleteTargetId !== null || isDeleting) return;
                    handleRowClick(assignmentTemplate.id);
                  }}
                >
                  <TableCell className="font-medium text-sm text-foreground">
                    {assignmentTemplate.title}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {assignmentTemplate.category ?? '-'}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    <StatusBadge status={assignmentTemplate.status ?? 'ACTIVE'} />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {assignmentTemplate.gradingMode}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {assignmentTemplate.scoringPolicy}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {assignmentTemplate.questions.length}
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
                            router.push(`/dashboard/assignment-templates/${assignmentTemplate.id}/edit`);
                          }}
                        >
                          <Pencil className="h-4 w-4" />
                          <span className="sr-only">Edit</span>
                        </Button>
                        <AlertDialog
                          open={deleteTargetId === assignmentTemplate.id}
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
                                setDeleteTargetId(assignmentTemplate.id);
                              }}
                            >
                              <Trash2 className="h-4 w-4" />
                              <span className="sr-only">Delete</span>
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete Assignment Template</AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to delete &quot;{assignmentTemplate.title}&quot;?
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
function describeDeleteConflict(detail?: string): string {
  const text = detail?.toLowerCase() ?? '';
  if (text.includes('must be archived')) {
    return 'Cannot delete — this assignment template has already been used. Archive it instead.';
  }
  if (text.includes('archived assignment template')) {
    return 'Cannot delete — archived templates must be purged from the archive manager.';
  }
  return 'Cannot delete — assignment template is referenced by assignments.';
}
