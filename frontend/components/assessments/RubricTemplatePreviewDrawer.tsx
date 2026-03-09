'use client';

import { useEffect, useState } from 'react';
import { ArrowUpRight, Loader2, Pencil } from 'lucide-react';

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { getRubric, type Rubric } from '@/lib/rubric-api';
import RubricGridPreview from '@/components/rubrics/RubricGridPreview';

type ApiError = { response?: { data?: { detail?: string } } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

type RubricTemplatePreviewDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rubricId: number | null;
  onEditRubric?: (rubricId: number) => void;
  onOpenFullEditor?: (rubricId: number) => void;
};

export default function RubricTemplatePreviewDrawer({
  open,
  onOpenChange,
  rubricId,
  onEditRubric,
  onOpenFullEditor,
}: RubricTemplatePreviewDrawerProps) {
  const [rubric, setRubric] = useState<Rubric | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadRubric() {
      if (!open || rubricId == null) {
        setRubric(null);
        setLoadError(null);
        return;
      }
      setIsLoading(true);
      setLoadError(null);
      try {
        const data = await getRubric(rubricId);
        if (!cancelled) setRubric(data);
      } catch (error: unknown) {
        if (!cancelled) {
          setRubric(null);
          setLoadError(extractDetail(error, 'Failed to load rubric template.'));
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadRubric();
    return () => {
      cancelled = true;
    };
  }, [open, rubricId]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[96vw] sm:max-w-4xl p-0">
        <SheetHeader className="border-b border-border">
          <SheetTitle>Rubric Template Preview</SheetTitle>
          <SheetDescription>
            Review rubric criteria and scoring levels before attaching.
          </SheetDescription>
          {rubricId != null && (onEditRubric || onOpenFullEditor) && (
            <div className="pt-2 flex flex-wrap gap-2">
              {onEditRubric && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => onEditRubric(rubricId)}
                >
                  <Pencil className="mr-1 h-4 w-4" />
                  Edit in Drawer
                </Button>
              )}
              {onOpenFullEditor && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => onOpenFullEditor(rubricId)}
                >
                  <ArrowUpRight className="mr-1 h-4 w-4" />
                  Open Full Editor
                </Button>
              )}
            </div>
          )}
        </SheetHeader>

        <div className="p-4 space-y-4 overflow-y-auto">
          {rubricId == null && (
            <p className="text-sm text-muted-foreground">
              Select a rubric first to preview it.
            </p>
          )}

          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading rubric...
            </div>
          )}

          {loadError && <p className="text-sm text-destructive">{loadError}</p>}

          {rubric && !isLoading && !loadError && (
            <>
              <div className="rounded-sm border border-border bg-card p-3 space-y-1">
                <h3 className="text-sm font-semibold text-foreground">{rubric.title}</h3>
                {rubric.description && (
                  <p className="text-xs text-muted-foreground">{rubric.description}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Status: {rubric.status} • Criteria: {rubric.criteria.length}
                </p>
              </div>

              <RubricGridPreview
                criteria={rubric.criteria}
                title={`Template Grid — ${rubric.title}`}
              />
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
