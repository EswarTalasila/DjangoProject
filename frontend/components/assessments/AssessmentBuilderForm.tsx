'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  type Assessment,
  type AssessmentInput,
  type QuestionInput,
  type GradingMode,
  type QuestionKind,
  getAssessment,
  createAssessment,
  updateAssessment,
} from '@/lib/assessment-api';
import QuestionBlock from './QuestionBlock';

// -- Error handling --

type ApiError = { response?: { data?: { detail?: string }; status?: number } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

function getStatusCode(error: unknown): number | undefined {
  return (error as ApiError).response?.status;
}

// -- Constants --

const GRADING_MODES: { value: GradingMode; label: string }[] = [
  { value: 'AUTO', label: 'Auto' },
  { value: 'MANUAL', label: 'Manual' },
  { value: 'HYBRID', label: 'Hybrid' },
  { value: 'RUBRIC', label: 'Rubric' },
  { value: 'REFLECTION', label: 'Reflection' },
  { value: 'MOOD_METER', label: 'Mood Meter' },
];

/** Default empty MCQ question appended when clicking "Add Question". */
function emptyMcqQuestion(): QuestionInput {
  return {
    type: 'MULTIPLE_CHOICE' as QuestionKind,
    prompt: '',
    maxPoints: 0,
    data: { choices: [{ prompt: '', score: 0 }], selectAll: false },
  };
}

// -- Props --

type AssessmentBuilderFormProps = {
  mode: 'create' | 'edit';
  assessmentId?: number;
};

export default function AssessmentBuilderForm({
  mode,
  assessmentId,
}: AssessmentBuilderFormProps) {
  const router = useRouter();

  // Form state
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('');
  const [gradingMode, setGradingMode] = useState<GradingMode>('AUTO');
  const [questions, setQuestions] = useState<QuestionInput[]>([emptyMcqQuestion()]);
  const [rubricId, setRubricId] = useState<string>('');
  const [rubricAssessmentIds, setRubricAssessmentIds] = useState<string>('');

  // UI state
  const [titleError, setTitleError] = useState<string | null>(null);
  const [questionsError, setQuestionsError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(mode === 'edit');

  // -- Edit mode: fetch existing assessment --

  useEffect(() => {
    if (mode !== 'edit' || !assessmentId) return;

    let cancelled = false;

    async function load() {
      try {
        const a: Assessment = await getAssessment(assessmentId!);
        if (cancelled) return;

        setTitle(a.title);
        setCategory(a.category ?? '');
        setGradingMode(a.gradingMode);
        setRubricId(a.rubricId != null ? String(a.rubricId) : '');
        setRubricAssessmentIds(
          a.rubricAssessmentIds.length > 0 ? a.rubricAssessmentIds.join(', ') : '',
        );

        // Map existing questions to QuestionInput shape
        if (a.questions.length > 0) {
          setQuestions(
            a.questions.map((q) => ({
              type: q.type,
              prompt: q.prompt,
              maxPoints: q.maxPoints,
              data: q.data ?? undefined,
            })),
          );
        }
      } catch {
        if (!cancelled) {
          toast.error('Failed to load assessment');
          router.push('/dashboard/assessments');
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [mode, assessmentId, router]);

  // -- Question array helpers --

  const handleQuestionChange = useCallback((index: number, updated: QuestionInput) => {
    setQuestions((prev) => prev.map((q, i) => (i === index ? updated : q)));
  }, []);

  const handleQuestionRemove = useCallback((index: number) => {
    setQuestions((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleMoveUp = useCallback((index: number) => {
    setQuestions((prev) => {
      const copy = [...prev];
      [copy[index - 1], copy[index]] = [copy[index], copy[index - 1]];
      return copy;
    });
  }, []);

  const handleMoveDown = useCallback((index: number) => {
    setQuestions((prev) => {
      const copy = [...prev];
      [copy[index], copy[index + 1]] = [copy[index + 1], copy[index]];
      return copy;
    });
  }, []);

  function addQuestion() {
    setQuestions((prev) => [...prev, emptyMcqQuestion()]);
  }

  // -- Validation --

  function validate(): boolean {
    let valid = true;

    // Title is required
    if (!title.trim()) {
      setTitleError('Title is required');
      valid = false;
    } else {
      setTitleError(null);
    }

    // Questions validation (skip for MOOD_METER)
    if (gradingMode !== 'MOOD_METER') {
      if (questions.length === 0) {
        setQuestionsError('At least one question is required');
        valid = false;
      } else if (questions.some((q) => !q.prompt.trim())) {
        setQuestionsError('Every question must have a non-empty prompt');
        valid = false;
      } else {
        setQuestionsError(null);
      }
    } else {
      setQuestionsError(null);
    }

    return valid;
  }

  // -- Submit --

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);

    // Build payload
    const payload: AssessmentInput = {
      title: title.trim(),
      category: category.trim() || null,
      gradingMode,
      questions: gradingMode === 'MOOD_METER' ? [] : questions,
    };

    // Include rubric fields when in RUBRIC mode
    if (gradingMode === 'RUBRIC') {
      payload.rubricId = rubricId ? Number(rubricId) : null;
      payload.rubricAssessmentIds = rubricAssessmentIds
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
        .map(Number)
        .filter((n) => !isNaN(n));
    }

    try {
      if (mode === 'create') {
        const created = await createAssessment(payload);
        toast.success('Assessment created');
        router.push(`/dashboard/assessments/${created.id}`);
      } else {
        await updateAssessment(assessmentId!, payload);
        toast.success('Assessment updated');
        router.push(`/dashboard/assessments/${assessmentId}`);
      }
    } catch (err: unknown) {
      if (mode === 'edit' && getStatusCode(err) === 409) {
        toast.error(
          'This assessment is referenced by assignments and cannot be modified',
        );
      } else {
        toast.error(extractDetail(err, 'Failed to save assessment'));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  // -- Cancel --

  function handleCancel() {
    if (mode === 'edit' && assessmentId) {
      router.push(`/dashboard/assessments/${assessmentId}`);
    } else {
      router.push('/dashboard/assessments');
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
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Metadata section */}
      <div className="rounded-sm border border-border bg-card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Assessment Details</h2>

        <div className="space-y-2">
          <Label htmlFor="title">Title</Label>
          <Input
            id="title"
            placeholder="Enter assessment title..."
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (titleError) setTitleError(null);
            }}
          />
          {titleError && <p className="text-sm text-destructive">{titleError}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="category">Category</Label>
          <Input
            id="category"
            placeholder="Optional category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="gradingMode">Grading Mode</Label>
          <Select
            value={gradingMode}
            onValueChange={(v) => setGradingMode(v as GradingMode)}
          >
            <SelectTrigger id="gradingMode">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {GRADING_MODES.map((gm) => (
                <SelectItem key={gm.value} value={gm.value}>
                  {gm.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Mood Meter info */}
      {gradingMode === 'MOOD_METER' && (
        <p className="text-sm text-muted-foreground bg-muted p-3 rounded">
          Mood Meter assessments use a single auto-configured question.
        </p>
      )}

      {/* Rubric fields */}
      {gradingMode === 'RUBRIC' && (
        <div className="rounded-sm border border-border bg-card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-foreground">Rubric Configuration</h2>

          <div className="space-y-2">
            <Label htmlFor="rubricId">Rubric ID</Label>
            <Input
              id="rubricId"
              type="number"
              placeholder="Rubric ID"
              value={rubricId}
              onChange={(e) => setRubricId(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="rubricAssessmentIds">Rubric Assessment IDs</Label>
            <Input
              id="rubricAssessmentIds"
              placeholder="Comma-separated IDs (e.g. 1, 2, 3)"
              value={rubricAssessmentIds}
              onChange={(e) => setRubricAssessmentIds(e.target.value)}
            />
          </div>
        </div>
      )}

      {/* Question builder (hidden for MOOD_METER) */}
      {gradingMode !== 'MOOD_METER' && (
        <div className="rounded-sm border border-border bg-card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-foreground">
            Questions ({questions.length})
          </h2>

          {questionsError && (
            <p className="text-sm text-destructive">{questionsError}</p>
          )}

          <div className="space-y-4">
            {questions.map((q, i) => (
              <QuestionBlock
                key={i}
                index={i}
                question={q}
                onChange={(updated) => handleQuestionChange(i, updated)}
                onRemove={() => handleQuestionRemove(i)}
                onMoveUp={i === 0 ? null : () => handleMoveUp(i)}
                onMoveDown={i === questions.length - 1 ? null : () => handleMoveDown(i)}
              />
            ))}
          </div>

          <Button type="button" variant="outline" onClick={addQuestion}>
            <Plus className="mr-2 h-4 w-4" />
            Add Question
          </Button>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {mode === 'create' ? 'Create Assessment' : 'Save Changes'}
        </Button>
        <Button type="button" variant="outline" onClick={handleCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
