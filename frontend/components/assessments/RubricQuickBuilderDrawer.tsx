'use client';

import { useEffect, useMemo, useState } from 'react';
import { Loader2, Plus, ArrowUpRight } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { HelpTip } from '@/components/ui/help-tip';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  createRubric,
  getRubric,
  type CriterionInput,
  type Rubric,
  type RubricInput,
  updateRubric,
} from '@/lib/rubric-api';
import CriterionBlock from '@/components/rubrics/CriterionBlock';
import RubricGridPreview from '@/components/rubrics/RubricGridPreview';

type ApiError = { response?: { data?: { detail?: string } } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

function emptyCriterion(): CriterionInput {
  return {
    title: '',
    description: '',
    weight: 1,
    levels: [{ label: '', points: 0, description: '' }],
  };
}

type RubricQuickBuilderDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: (rubric: Rubric) => void;
  onSaved?: (rubric: Rubric) => void;
  mode?: 'create' | 'edit';
  rubricId?: number | null;
  onOpenFullEditor?: (rubricId?: number | null) => void;
};

export default function RubricQuickBuilderDrawer({
  open,
  onOpenChange,
  onCreated,
  onSaved,
  mode = 'create',
  rubricId = null,
  onOpenFullEditor,
}: RubricQuickBuilderDrawerProps) {
  const isEditMode = mode === 'edit' && rubricId != null;
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [criteria, setCriteria] = useState<CriterionInput[]>([emptyCriterion()]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showTips, setShowTips] = useState(true);

  const titleError = useMemo(() => {
    if (!title.trim()) return 'Title is required';
    return null;
  }, [title]);

  const criteriaError = useMemo(() => {
    if (criteria.length === 0) return 'At least one criterion is required';
    if (criteria.some((c) => !c.title.trim())) {
      return 'Each criterion needs a title';
    }
    if (criteria.some((c) => (c.levels ?? []).length === 0)) {
      return 'Each criterion needs at least one level';
    }
    if (criteria.some((c) => (c.levels ?? []).some((l) => !l.label.trim()))) {
      return 'Each level needs a label';
    }
    return null;
  }, [criteria]);

  function resetForm() {
    setTitle('');
    setDescription('');
    setCriteria([emptyCriterion()]);
  }

  useEffect(() => {
    let cancelled = false;

    async function loadRubricForEdit() {
      if (!open || !isEditMode || rubricId == null) {
        if (!open) {
          resetForm();
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      try {
        const rubric = await getRubric(rubricId);
        if (cancelled) return;
        setTitle(rubric.title);
        setDescription(rubric.description ?? '');
        setCriteria(
          rubric.criteria.length > 0
            ? rubric.criteria.map((criterion) => ({
                title: criterion.title,
                description: criterion.description,
                weight: criterion.weight,
                levels:
                  criterion.levels.length > 0
                    ? criterion.levels.map((level) => ({
                        label: level.label,
                        points: level.points,
                        description: level.description,
                      }))
                    : [{ label: '', points: 0, description: '' }],
              }))
            : [emptyCriterion()],
        );
      } catch (error: unknown) {
        if (cancelled) return;
        toast.error(extractDetail(error, 'Failed to load rubric template.'));
        onOpenChange(false);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadRubricForEdit();
    return () => {
      cancelled = true;
    };
  }, [open, isEditMode, rubricId, onOpenChange]);

  function addCriterion() {
    setCriteria((prev) => [...prev, emptyCriterion()]);
  }

  function handleCriterionChange(index: number, updated: CriterionInput) {
    setCriteria((prev) => prev.map((c, i) => (i === index ? updated : c)));
  }

  function handleCriterionRemove(index: number) {
    setCriteria((prev) => prev.filter((_, i) => i !== index));
  }

  function handleMoveUp(index: number) {
    if (index <= 0) return;
    setCriteria((prev) => {
      const copy = [...prev];
      [copy[index - 1], copy[index]] = [copy[index], copy[index - 1]];
      return copy;
    });
  }

  function handleMoveDown(index: number) {
    setCriteria((prev) => {
      if (index >= prev.length - 1) return prev;
      const copy = [...prev];
      [copy[index], copy[index + 1]] = [copy[index + 1], copy[index]];
      return copy;
    });
  }

  async function handleSave() {
    if (isLoading) return;
    if (titleError || criteriaError) {
      toast.error(titleError ?? criteriaError ?? 'Invalid rubric input');
      return;
    }

    setIsSaving(true);
    const payload: RubricInput = {
      title: title.trim(),
      description: description.trim(),
      criteria: criteria.map((c, cIdx) => ({
        title: c.title.trim(),
        description: (c.description ?? '').trim(),
        orderIndex: cIdx,
        weight: c.weight ?? 1,
        levels: (c.levels ?? []).map((l, lIdx) => ({
          label: l.label.trim(),
          points: l.points,
          description: (l.description ?? '').trim(),
          orderIndex: lIdx,
        })),
      })),
    };

    try {
      if (isEditMode && rubricId != null) {
        const updated = await updateRubric(rubricId, payload);
        toast.success('Rubric updated');
        onSaved?.(updated);
        onOpenChange(false);
        return;
      }

      const created = await createRubric(payload);
      toast.success('Rubric created');
      onCreated?.(created);
      onSaved?.(created);
      resetForm();
      onOpenChange(false);
    } catch (error: unknown) {
      toast.error(
        extractDetail(
          error,
          isEditMode ? 'Failed to update rubric.' : 'Failed to create rubric.',
        ),
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        if (!next && !isSaving) {
          resetForm();
        }
      }}
    >
      <SheetContent side="right" className="w-[92vw] sm:max-w-2xl p-0">
        <SheetHeader className="border-b border-border">
          <SheetTitle>{isEditMode ? 'Quick Edit Rubric' : 'Quick Rubric Builder'}</SheetTitle>
          <SheetDescription>
            {isEditMode
              ? 'Edit this rubric template without leaving the assessment builder.'
              : 'Create a rubric template without leaving the assessment builder.'}
          </SheetDescription>
          <div className="pt-1 flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowTips((v) => !v)}
            >
              {showTips ? 'Hide Tips' : 'Show Tips'}
            </Button>
            {onOpenFullEditor && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onOpenFullEditor(isEditMode ? rubricId : null)}
              >
                <ArrowUpRight className="mr-1 h-4 w-4" />
                Open Full Editor
              </Button>
            )}
          </div>
        </SheetHeader>

        <div className="p-4 space-y-4 overflow-y-auto">
          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading rubric...
            </div>
          )}

          {!isLoading && (
            <>
              {showTips && (
                <div className="rounded border border-border bg-muted/40 p-3 text-xs text-muted-foreground space-y-1">
                  <p>Each criterion is a grading row.</p>
                  <p>Each level is a scoring column with points and optional description.</p>
                  <p>The grid preview updates live as you edit.</p>
                </div>
              )}
              <div className="space-y-2">
                <div className="flex items-center gap-1.5">
                  <Label htmlFor="quick-rubric-title">Title</Label>
                  <HelpTip text="Give this rubric a reusable template name so you can attach it to many assessments." />
                </div>
                <Input
                  id="quick-rubric-title"
                  placeholder="Enter rubric title..."
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
                {titleError && <p className="text-xs text-destructive">{titleError}</p>}
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-1.5">
                  <Label htmlFor="quick-rubric-description">Description</Label>
                  <HelpTip text="Optional note describing what this rubric measures." />
                </div>
                <Input
                  id="quick-rubric-description"
                  placeholder="Optional description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <h4 className="text-sm font-semibold text-foreground">
                      Criteria ({criteria.length})
                    </h4>
                    <HelpTip text="Criteria are rows. Add levels to define scoring columns for each row." />
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={addCriterion}>
                    <Plus className="mr-1 h-4 w-4" /> Add Criterion
                  </Button>
                </div>

                {criteriaError && <p className="text-xs text-destructive">{criteriaError}</p>}

                <div className="space-y-3">
                  {criteria.map((criterion, index) => (
                    <CriterionBlock
                      key={index}
                      index={index}
                      criterion={criterion}
                      onChange={(updated) => handleCriterionChange(index, updated)}
                      onRemove={() => handleCriterionRemove(index)}
                      onMoveUp={index === 0 ? null : () => handleMoveUp(index)}
                      onMoveDown={
                        index === criteria.length - 1 ? null : () => handleMoveDown(index)
                      }
                    />
                  ))}
                </div>
              </div>

              <RubricGridPreview criteria={criteria} title="Live Rubric Preview" />
            </>
          )}
        </div>

        <SheetFooter className="border-t border-border">
          <div className="flex items-center justify-end gap-2 w-full">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSaving || isLoading}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={() => void handleSave()}
              disabled={isSaving || isLoading}
            >
              {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEditMode ? 'Save Rubric' : 'Create Rubric'}
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
