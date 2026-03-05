'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Archive, Pencil, Plus, Search, Trash2 } from 'lucide-react';
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
  archiveRubric,
  deleteRubric,
  listRubrics,
  type Rubric,
} from '@/lib/rubric-api';

type ApiError = { response?: { data?: { detail?: string }; status?: number } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

type RubricListViewProps = {
  canManage: boolean;
};

export default function RubricListView({ canManage }: RubricListViewProps) {
  const router = useRouter();

  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadRubrics = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await listRubrics();
      setRubrics(data);
    } catch {
      setLoadError('Failed to load rubrics.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    setIsLoading(true);
    void loadRubrics();
  }, [loadRubrics]);

  const filteredRubrics = useMemo(() => {
    if (!searchQuery.trim()) return rubrics;
    const query = searchQuery.toLowerCase();
    return rubrics.filter((r) => r.title.toLowerCase().includes(query));
  }, [rubrics, searchQuery]);

  async function handleDelete() {
    if (deleteTargetId === null) return;

    setIsDeleting(true);
    try {
      await deleteRubric(deleteTargetId);
      toast.success('Rubric deleted.');
      setDeleteTargetId(null);
      await loadRubrics();
    } catch (error: unknown) {
      if (
        (error as ApiError).response?.data?.detail?.toLowerCase().includes('referenced') ||
        (error as ApiError).response?.status === 409
      ) {
        toast.error('Cannot delete — rubric is referenced by assessments.');
      } else {
        toast.error(extractDetail(error, 'Failed to delete rubric.'));
      }
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleArchive(id: number) {
    try {
      await archiveRubric(id);
      toast.success('Rubric archived.');
      await loadRubrics();
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to archive rubric.'));
    }
  }

  function handleRowClick(id: number) {
    router.push(`/dashboard/rubrics/${id}`);
  }

  function statusBadgeClasses(status: string): string {
    if (status === 'ARCHIVED') {
      return 'bg-status-warning-bg text-foreground';
    }
    return 'bg-status-success-bg text-foreground';
  }

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            Rubrics
          </h1>
          <p className="text-muted-foreground mt-1">
            {canManage
              ? 'Manage rubrics and their grading criteria.'
              : 'View rubrics and their grading criteria.'}
          </p>
        </div>
        {canManage && (
          <Button onClick={() => router.push('/dashboard/rubrics/new')}>
            <Plus className="mr-2 h-4 w-4" />
            Create Rubric
          </Button>
        )}
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search rubrics..."
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
        <p className="text-sm text-muted-foreground">Loading rubrics...</p>
      )}

      {/* Empty state */}
      {!isLoading && !loadError && filteredRubrics.length === 0 && (
        <div className="rounded-sm border border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            {rubrics.length === 0
              ? 'No rubrics yet.'
              : 'No rubrics match your search.'}
          </p>
        </div>
      )}

      {/* Rubric table */}
      {!isLoading && !loadError && filteredRubrics.length > 0 && (
        <div className="rounded-sm border border-border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted border-b border-border">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Title
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Status
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Criteria
                </TableHead>
                {canManage && (
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground text-right">
                    Actions
                  </TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRubrics.map((rubric) => (
                <TableRow
                  key={rubric.id}
                  className="even:bg-muted/50 hover:bg-accent transition-colors cursor-pointer"
                  onClick={() => handleRowClick(rubric.id)}
                >
                  <TableCell className="font-medium text-sm text-foreground">
                    {rubric.title}
                  </TableCell>
                  <TableCell>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${statusBadgeClasses(rubric.status)}`}
                    >
                      {rubric.status}
                    </span>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {rubric.criteria.length}
                  </TableCell>
                  {canManage && (
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {rubric.status === 'ACTIVE' && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={(e) => {
                              e.stopPropagation();
                              void handleArchive(rubric.id);
                            }}
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
                          onClick={(e) => {
                            e.stopPropagation();
                            router.push(`/dashboard/rubrics/${rubric.id}/edit`);
                          }}
                        >
                          <Pencil className="h-4 w-4" />
                          <span className="sr-only">Edit</span>
                        </Button>
                        <AlertDialog
                          open={deleteTargetId === rubric.id}
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
                                setDeleteTargetId(rubric.id);
                              }}
                            >
                              <Trash2 className="h-4 w-4" />
                              <span className="sr-only">Delete</span>
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete Rubric</AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to delete &quot;{rubric.title}&quot;?
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
