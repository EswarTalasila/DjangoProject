'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Plus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { HelpTip } from '@/components/ui/help-tip';
import {
  type Rubric,
  type RubricInput,
  type CriterionInput,
  getRubric,
  createRubric,
  updateRubric,
} from '@/lib/rubric-api';
import CriterionBlock from './CriterionBlock';
import RubricGridPreview from './RubricGridPreview';

// -- Error handling --

type ApiError = { response?: { data?: { detail?: string }; status?: number } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

function getStatusCode(error: unknown): number | undefined {
  return (error as ApiError).response?.status;
}

// -- Helpers --

function emptyCriterion(): CriterionInput {
  return {
    title: '',
    description: '',
    weight: 1,
    levels: [{ label: '', points: 0, description: '' }],
  };
}

// -- Props --

type RubricBuilderFormProps = {
  mode: 'create' | 'edit';
  rubricId?: number;
};

export default function RubricBuilderForm({
  mode,
  rubricId,
}: RubricBuilderFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const returnTo = useMemo(() => {
    const raw = searchParams.get('returnTo');
    if (!raw) return null;
    if (!raw.startsWith('/dashboard/assessments')) return null;
    return raw;
  }, [searchParams]);

  function resolveReturnTargetWithRubric(id?: number): string | null {
    if (!returnTo) return null;
    if (id == null) return returnTo;
    const separator = returnTo.includes('?') ? '&' : '?';
    return `${returnTo}${separator}newRubricId=${id}`;
  }

  // Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [criteria, setCriteria] = useState<CriterionInput[]>([emptyCriterion()]);

  // UI state
  const [titleError, setTitleError] = useState<string | null>(null);
  const [criteriaError, setCriteriaError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(mode === 'edit');
  const [showTips, setShowTips] = useState(true);

  // -- Edit mode: fetch existing rubric --

  useEffect(() => {
    if (mode !== 'edit' || !rubricId) return;

    let cancelled = false;

    async function load() {
      try {
        const r: Rubric = await getRubric(rubricId!);
        if (cancelled) return;

        setTitle(r.title);
        setDescription(r.description);

        if (r.criteria.length > 0) {
          setCriteria(
            r.criteria.map((c) => ({
              title: c.title,
              description: c.description,
              weight: c.weight,
              levels: c.levels.map((l) => ({
                label: l.label,
                points: l.points,
                description: l.description,
              })),
            })),
          );
        }
      } catch {
        if (!cancelled) {
          toast.error('Failed to load rubric');
          router.push('/dashboard/rubrics');
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [mode, rubricId, router]);

  // -- Criteria array helpers --

  const handleCriterionChange = useCallback((index: number, updated: CriterionInput) => {
    setCriteria((prev) => prev.map((c, i) => (i === index ? updated : c)));
  }, []);

  const handleCriterionRemove = useCallback((index: number) => {
    setCriteria((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleMoveUp = useCallback((index: number) => {
    setCriteria((prev) => {
      const copy = [...prev];
      [copy[index - 1], copy[index]] = [copy[index], copy[index - 1]];
      return copy;
    });
  }, []);

  const handleMoveDown = useCallback((index: number) => {
    setCriteria((prev) => {
      const copy = [...prev];
      [copy[index], copy[index + 1]] = [copy[index + 1], copy[index]];
      return copy;
    });
  }, []);

  function addCriterion() {
    setCriteria((prev) => [...prev, emptyCriterion()]);
  }

  // -- Validation --

  function validate(): boolean {
    let valid = true;

    if (!title.trim()) {
      setTitleError('Title is required');
      valid = false;
    } else {
      setTitleError(null);
    }

    if (criteria.length === 0) {
      setCriteriaError('At least one criterion is required');
      valid = false;
    } else if (criteria.some((c) => !c.title.trim())) {
      setCriteriaError('Every criterion must have a title');
      valid = false;
    } else {
      setCriteriaError(null);
    }

    return valid;
  }

  // -- Submit --

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);

    const payload: RubricInput = {
      title: title.trim(),
      description: description.trim(),
      criteria: criteria.map((c, idx) => ({
        title: c.title.trim(),
        description: (c.description ?? '').trim(),
        orderIndex: idx,
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
      if (mode === 'create') {
        const created = await createRubric(payload);
        toast.success('Rubric created');
        const target = resolveReturnTargetWithRubric(created.id);
        if (target) {
          router.push(target);
        } else {
          router.push(`/dashboard/rubrics/${created.id}`);
        }
      } else {
        await updateRubric(rubricId!, payload);
        toast.success('Rubric updated');
        const target = resolveReturnTargetWithRubric(rubricId);
        if (target) {
          router.push(target);
        } else {
          router.push(`/dashboard/rubrics/${rubricId}`);
        }
      }
    } catch (err: unknown) {
      if (mode === 'edit' && getStatusCode(err) === 409) {
        toast.error(
          'This rubric is referenced by assessments and cannot be modified',
        );
      } else {
        toast.error(extractDetail(err, 'Failed to save rubric'));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  // -- Cancel --

  function handleCancel() {
    if (returnTo) {
      router.push(returnTo);
      return;
    }
    if (mode === 'edit' && rubricId) {
      router.push(`/dashboard/rubrics/${rubricId}`);
    } else {
      router.push('/dashboard/rubrics');
    }
  }

  // -- Render --

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(320px,1fr)_minmax(0,2fr)] gap-4 items-start">
        <section className="space-y-6 min-w-0">
      {/* Metadata section */}
      <div className="rounded-sm border border-border bg-card p-6 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-foreground">Rubric Details</h2>
          <Button type="button" variant="outline" size="sm" onClick={() => setShowTips((v) => !v)}>
            {showTips ? 'Hide Tips' : 'Show Tips'}
          </Button>
        </div>

        {showTips && (
          <div className="rounded border border-border bg-muted/40 p-3 text-xs text-muted-foreground space-y-1">
            <p>Define criteria as rows and levels as scoring columns.</p>
            <p>Weights should stay above 0 and points should be non-negative.</p>
            <p>Use the live preview below to verify rubric structure before saving.</p>
          </div>
        )}

        <div className="space-y-2">
          <div className="flex items-center gap-1.5">
            <Label htmlFor="title">Title</Label>
            <HelpTip text="Name this rubric template so researchers and teachers can identify it quickly." />
          </div>
          <Input
            id="title"
            placeholder="Enter rubric title..."
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (titleError) setTitleError(null);
            }}
          />
          {titleError && <p className="text-sm text-destructive">{titleError}</p>}
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-1.5">
            <Label htmlFor="description">Description</Label>
            <HelpTip text="Optional context for when to use this rubric (for example: writing quality, presentation skills)." />
          </div>
          <Input
            id="description"
            placeholder="Optional description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>

      {/* Criteria builder */}
      <div className="rounded-sm border border-border bg-card p-6 space-y-4">
        <div className="flex items-center gap-1.5">
          <h2 className="text-lg font-semibold text-foreground">
            Criteria ({criteria.length})
          </h2>
          <HelpTip text="Criteria are rubric rows. Levels inside each criterion are score columns." />
        </div>

        {criteriaError && (
          <p className="text-sm text-destructive">{criteriaError}</p>
        )}

        <div className="space-y-4">
          {criteria.map((c, i) => (
            <CriterionBlock
              key={i}
              index={i}
              criterion={c}
              onChange={(updated) => handleCriterionChange(i, updated)}
              onRemove={() => handleCriterionRemove(i)}
              onMoveUp={i === 0 ? null : () => handleMoveUp(i)}
              onMoveDown={i === criteria.length - 1 ? null : () => handleMoveDown(i)}
            />
          ))}
        </div>

        <Button type="button" variant="outline" onClick={addCriterion}>
          <Plus className="mr-2 h-4 w-4" />
          Add Criterion
        </Button>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {mode === 'create' ? 'Create Rubric' : 'Save Changes'}
        </Button>
        <Button type="button" variant="outline" onClick={handleCancel}>
          Cancel
        </Button>
      </div>
      </section>

      <aside className="rounded-sm border border-border bg-card p-4 xl:sticky xl:top-4 max-h-[calc(100vh-180px)] overflow-y-auto">
        <RubricGridPreview criteria={criteria} title="Live Rubric Grid Preview" />
      </aside>
      </div>
    </form>
  );
}
