'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import {
  Plus,
  Loader2,
  GripVertical,
} from 'lucide-react';
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
import { HelpTip } from '@/components/ui/help-tip';
import {
  type Assessment,
  type AssessmentInput,
  type QuestionInput,
  type GradingMode,
  type ScoringPolicy,
  type QuestionKind,
  type QuestionGroupInput,
  getAssessment,
  createAssessment,
  listAssessments,
  updateAssessment,
} from '@/lib/assessment-api';
import { listRubrics, type Rubric } from '@/lib/rubric-api';
import { toErrorMessage } from '@/lib/utils';
import QuestionEditor from './QuestionEditor';
import QuestionGroupPanel from './QuestionGroupPanel';
import AssessmentActionBar from './AssessmentActionBar';

// -- Error handling --

function getStatusCode(error: unknown): number | undefined {
  return (error as { response?: { status?: number } }).response?.status;
}

// -- Constants --

type BuilderGradingMode = 'AUTO' | 'MANUAL' | 'HYBRID';

const GRADING_MODES: { value: BuilderGradingMode; label: string }[] = [
  { value: 'AUTO', label: 'Auto' },
  { value: 'MANUAL', label: 'Manual' },
  { value: 'HYBRID', label: 'Hybrid' },
];

const SCORING_POLICIES: { value: ScoringPolicy; label: string }[] = [
  { value: 'STANDARD', label: 'Standard scoring' },
  { value: 'COMPLETION', label: 'Completion (100 on submit)' },
];

/** Default empty MCQ question appended when clicking "Add Question". */
function emptyMcqQuestion(): QuestionInput {
  return {
    type: 'MULTIPLE_CHOICE' as QuestionKind,
    prompt: '',
    maxPoints: 0,
    data: { choices: [{ prompt: '', score: 0 }], selectAll: false },
    gradingStrategy: 'AUTO',
  };
}

function makeGroupName(nextIndex: number): string {
  return `Group ${nextIndex}`;
}

function makeGroupKey(nextIndex: number): string {
  return `group-${Date.now()}-${nextIndex}`;
}

function normalizeBuilderMode(mode: GradingMode): BuilderGradingMode {
  if (mode === 'AUTO' || mode === 'MANUAL' || mode === 'HYBRID') return mode;
  return 'MANUAL';
}

function formatQuestionKind(kind: QuestionKind): string {
  switch (kind) {
    case 'MULTIPLE_CHOICE':
      return 'Multiple Choice';
    case 'SHORT_ANSWER':
      return 'Short Answer';
    case 'NUMBER_SCALE':
      return 'Number Scale';
    case 'MOOD_METER':
      return 'Mood Meter';
    case 'FILE_UPLOAD':
      return 'File Upload';
    default:
      return kind;
  }
}

function normalizeQuestionKind(kind: string): QuestionKind {
  if (kind === 'MULTIPLE_CHOICE' || kind === 'SHORT_ANSWER' || kind === 'NUMBER_SCALE' || kind === 'MOOD_METER' || kind === 'FILE_UPLOAD') {
    return kind;
  }
  return 'SHORT_ANSWER';
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
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Form state
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('');
  const [categoryDraft, setCategoryDraft] = useState('');
  const [isCategoryComposerOpen, setIsCategoryComposerOpen] = useState(false);
  const [gradingMode, setGradingMode] = useState<BuilderGradingMode>('AUTO');
  const [scoringPolicy, setScoringPolicy] = useState<ScoringPolicy>('STANDARD');
  const [questions, setQuestions] = useState<QuestionInput[]>([emptyMcqQuestion()]);
  const [questionGroups, setQuestionGroups] = useState<QuestionGroupInput[]>([]);
  const [categoryOptions, setCategoryOptions] = useState<string[]>([]);

  // Selection / editor state
  const [selectedQuestionIndex, setSelectedQuestionIndex] = useState(0);
  const [selectedQuestionIndices, setSelectedQuestionIndices] = useState<number[]>([]);
  const [assignGroupKey, setAssignGroupKey] = useState('__NONE__');
  const [rubricApplyId, setRubricApplyId] = useState('__NONE__');
  const [newGroupName, setNewGroupName] = useState('');
  const [draggingQuestionIndex, setDraggingQuestionIndex] = useState<number | null>(
    null,
  );
  const [dragOverQuestionIndex, setDragOverQuestionIndex] = useState<number | null>(
    null,
  );

  // Rubric options
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [isRubricsLoading, setIsRubricsLoading] = useState(true);
  const [isQuickRubricOpen, setIsQuickRubricOpen] = useState(false);
  const [isQuickRubricEditOpen, setIsQuickRubricEditOpen] = useState(false);
  const [quickEditRubricId, setQuickEditRubricId] = useState<number | null>(null);
  const [isRubricPreviewOpen, setIsRubricPreviewOpen] = useState(false);
  const [previewRubricId, setPreviewRubricId] = useState<number | null>(null);

  // UI state
  const [titleError, setTitleError] = useState<string | null>(null);
  const [questionsError, setQuestionsError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(mode === 'edit');
  const [showTips, setShowTips] = useState(false);

  const rubricById = useMemo(() => {
    const map = new Map<number, Rubric>();
    for (const rubric of rubrics) {
      map.set(rubric.id, rubric);
    }
    return map;
  }, [rubrics]);

  const groupByKey = useMemo(() => {
    const map = new Map<string, QuestionGroupInput>();
    for (const group of questionGroups) {
      map.set(group.clientKey, group);
    }
    return map;
  }, [questionGroups]);

  const questionCountByGroupKey = useMemo(() => {
    const map = new Map<string, number>();
    for (const question of questions) {
      if (!question.groupClientKey) continue;
      map.set(
        question.groupClientKey,
        (map.get(question.groupClientKey) ?? 0) + 1,
      );
    }
    return map;
  }, [questions]);

  const isRubricEnabled = gradingMode !== 'AUTO';

  function isManualQuestion(q: QuestionInput, modeValue: BuilderGradingMode): boolean {
    if (modeValue === 'MANUAL') return true;
    if (modeValue === 'HYBRID') {
      return (q.gradingStrategy ?? 'AUTO') === 'MANUAL';
    }
    return false;
  }

  function effectiveRubricId(q: QuestionInput): number | null {
    if (q.rubricId != null) return q.rubricId;
    if (!q.groupClientKey) return null;
    const group = questionGroups.find((g) => g.clientKey === q.groupClientKey);
    return group?.rubricId ?? null;
  }

  // -- Load rubrics --

  useEffect(() => {
    let cancelled = false;

    async function loadRubrics() {
      try {
        const data = await listRubrics();
        if (!cancelled) {
          setRubrics(data);
        }
      } catch {
        if (!cancelled) {
          toast.error('Failed to load rubric templates.');
        }
      } finally {
        if (!cancelled) setIsRubricsLoading(false);
      }
    }

    void loadRubrics();

    async function loadCategoryOptions() {
      try {
        const items = await listAssessments();
        if (cancelled) return;
        const categories = Array.from(
          new Set(
            items
              .map((item) => item.category?.trim())
              .filter((value): value is string => Boolean(value)),
          ),
        ).sort((a, b) => a.localeCompare(b));
        setCategoryOptions(categories);
      } catch {
        if (!cancelled) {
          setCategoryOptions([]);
        }
      }
    }

    void loadCategoryOptions();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const storage = window.localStorage as
      | { getItem?: (key: string) => string | null }
      | undefined;
    if (!storage || typeof storage.getItem !== 'function') return;
    const stored = storage.getItem('assessmentBuilderShowTips');
    if (stored != null) {
      setShowTips(stored === '1');
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const storage = window.localStorage as
      | { setItem?: (key: string, value: string) => void }
      | undefined;
    if (!storage || typeof storage.setItem !== 'function') return;
    storage.setItem('assessmentBuilderShowTips', showTips ? '1' : '0');
  }, [showTips]);

  useEffect(() => {
    if (assignGroupKey === '__NONE__') return;
    if (!questionGroups.some((group) => group.clientKey === assignGroupKey)) {
      setAssignGroupKey('__NONE__');
    }
  }, [assignGroupKey, questionGroups]);

  useEffect(() => {
    if (!isCategoryComposerOpen) {
      setCategoryDraft(category);
    }
  }, [category, isCategoryComposerOpen]);

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
        setGradingMode(normalizeBuilderMode(a.gradingMode));
        setScoringPolicy(a.scoringPolicy ?? 'STANDARD');

        const mappedGroups: QuestionGroupInput[] = (a.questionGroups ?? []).map(
          (group, index) => ({
            clientKey: `group-${group.id}-${index}`,
            name: group.name,
            rubricId: group.rubricId,
          }),
        );
        setQuestionGroups(mappedGroups);

        const groupKeyById = new Map<number, string>();
        for (let i = 0; i < (a.questionGroups ?? []).length; i += 1) {
          groupKeyById.set(a.questionGroups[i].id, mappedGroups[i].clientKey);
        }

        if (a.questions.length > 0) {
          setQuestions(
            a.questions.map((q) => ({
              type: normalizeQuestionKind(String(q.type)),
              prompt: q.prompt,
              maxPoints: q.maxPoints,
              data: q.data ?? undefined,
              gradingStrategy: q.gradingStrategy,
              rubricId: q.rubricId,
              groupClientKey:
                q.groupId != null ? groupKeyById.get(q.groupId) : undefined,
            })),
          );
          setSelectedQuestionIndex(0);
        } else {
          setQuestions([emptyMcqQuestion()]);
          setSelectedQuestionIndex(0);
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

    void load();
    return () => {
      cancelled = true;
    };
  }, [mode, assessmentId, router]);

  // -- Question array helpers --

  const handleQuestionChange = useCallback((index: number, updated: QuestionInput) => {
    setQuestions((prev) => prev.map((q, i) => (i === index ? updated : q)));
  }, []);

  const handleQuestionRemove = useCallback((index: number) => {
    setQuestions((prev) => {
      const next = prev.filter((_, i) => i !== index);
      if (next.length === 0) {
        return [emptyMcqQuestion()];
      }
      return next;
    });

    setSelectedQuestionIndices((prev) =>
      prev.filter((i) => i !== index).map((i) => (i > index ? i - 1 : i)),
    );

    setSelectedQuestionIndex((prev) => {
      if (prev === index) {
        if (questions.length <= 1) return 0;
        return index === questions.length - 1 ? index - 1 : index;
      }
      if (prev > index) return prev - 1;
      return prev;
    });
  }, [questions.length]);

  const handleMoveUp = useCallback((index: number) => {
    if (index <= 0) return;
    setQuestions((prev) => {
      const copy = [...prev];
      [copy[index - 1], copy[index]] = [copy[index], copy[index - 1]];
      return copy;
    });

    setSelectedQuestionIndices((prev) =>
      prev.map((i) => {
        if (i === index) return index - 1;
        if (i === index - 1) return index;
        return i;
      }),
    );

    setSelectedQuestionIndex((prev) => {
      if (prev === index) return index - 1;
      if (prev === index - 1) return index;
      return prev;
    });
  }, []);

  const handleMoveDown = useCallback((index: number) => {
    if (index >= questions.length - 1) return;
    setQuestions((prev) => {
      const copy = [...prev];
      [copy[index], copy[index + 1]] = [copy[index + 1], copy[index]];
      return copy;
    });

    setSelectedQuestionIndices((prev) =>
      prev.map((i) => {
        if (i === index) return index + 1;
        if (i === index + 1) return index;
        return i;
      }),
    );

    setSelectedQuestionIndex((prev) => {
      if (prev === index) return index + 1;
      if (prev === index + 1) return index;
      return prev;
    });
  }, [questions.length]);

  function addQuestion() {
    setQuestions((prev) => {
      const next = [...prev, emptyMcqQuestion()];
      setSelectedQuestionIndex(next.length - 1);
      return next;
    });
  }

  function toggleSelectedQuestion(index: number, checked: boolean) {
    setSelectedQuestionIndices((prev) => {
      if (checked) {
        if (prev.includes(index)) return prev;
        return [...prev, index].sort((a, b) => a - b);
      }
      return prev.filter((i) => i !== index);
    });
  }

  function remapIndexAfterMove(index: number, from: number, to: number): number {
    if (index === from) return to;
    if (from < to && index > from && index <= to) return index - 1;
    if (from > to && index >= to && index < from) return index + 1;
    return index;
  }

  function moveQuestion(from: number, to: number) {
    if (from === to || from < 0 || to < 0 || from >= questions.length || to >= questions.length) {
      return;
    }

    setQuestions((prev) => {
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });

    setSelectedQuestionIndices((prev) =>
      prev
        .map((idx) => remapIndexAfterMove(idx, from, to))
        .sort((a, b) => a - b),
    );
    setSelectedQuestionIndex((prev) => remapIndexAfterMove(prev, from, to));
  }

  function addQuestionGroup(preferredName?: string) {
    const nextIndex = questionGroups.length + 1;
    const clientKey = makeGroupKey(nextIndex);
    const name = preferredName?.trim() || makeGroupName(nextIndex);
    setQuestionGroups((prev) => [
      ...prev,
      { clientKey, name, rubricId: null },
    ]);
    setAssignGroupKey(clientKey);
  }

  function updateQuestionGroup(
    clientKey: string,
    patch: Partial<QuestionGroupInput>,
  ) {
    setQuestionGroups((prev) =>
      prev.map((g) => (g.clientKey === clientKey ? { ...g, ...patch } : g)),
    );
  }

  function removeQuestionGroup(clientKey: string) {
    setQuestionGroups((prev) => prev.filter((g) => g.clientKey !== clientKey));
    setQuestions((prev) =>
      prev.map((q) =>
        q.groupClientKey === clientKey ? { ...q, groupClientKey: undefined } : q,
      ),
    );
  }

  function assignGroupToSelected() {
    if (
      assignGroupKey !== '__NONE__' &&
      !questionGroups.some((group) => group.clientKey === assignGroupKey)
    ) {
      toast.error('Select a valid group first.');
      return;
    }

    const targetIndices =
      selectedQuestionIndices.length > 0
        ? selectedQuestionIndices
        : [selectedQuestionIndex];

    setQuestions((prev) =>
      prev.map((q, i) => {
        if (!targetIndices.includes(i)) return q;
        return {
          ...q,
          groupClientKey: assignGroupKey === '__NONE__' ? undefined : assignGroupKey,
        };
      }),
    );

    toast.success(
      assignGroupKey === '__NONE__'
        ? 'Removed selected question(s) from group.'
        : 'Assigned selected question(s) to group.',
    );
  }

  function applyRubricToIndices(indices: number[], rubricId: number | null) {
    setQuestions((prev) =>
      prev.map((q, i) => {
        if (!indices.includes(i)) return q;
        const next: QuestionInput = { ...q, rubricId };
        if (gradingMode === 'HYBRID' && rubricId != null) {
          next.gradingStrategy = 'MANUAL';
        }
        return next;
      }),
    );
  }

  function applyRubricToSelectedQuestions() {
    if (!isRubricEnabled) {
      toast.error('Switch to MANUAL or HYBRID to attach rubrics.');
      return;
    }
    const targetIndices =
      selectedQuestionIndices.length > 0
        ? selectedQuestionIndices
        : [selectedQuestionIndex];

    const rubricId = rubricApplyId === '__NONE__' ? null : Number(rubricApplyId);

    applyRubricToIndices(targetIndices, rubricId);

    toast.success('Applied rubric to selected question(s).');
  }

  function createGroupFromInput() {
    if (!newGroupName.trim()) {
      toast.error('Enter a group name first.');
      return;
    }
    addQuestionGroup(newGroupName);
    setNewGroupName('');
    toast.success('Group created.');
  }

  function openCategoryComposer() {
    setCategoryDraft(category);
    setIsCategoryComposerOpen(true);
  }

  function cancelCategoryComposer() {
    setCategoryDraft(category);
    setIsCategoryComposerOpen(false);
  }

  function applyCategoryDraft() {
    const next = categoryDraft.trim();
    setCategory(next);
    setCategoryDraft(next);
    setIsCategoryComposerOpen(false);
  }

  function chooseCategoryFromBank(nextCategory: string) {
    setCategory(nextCategory);
    setCategoryDraft(nextCategory);
    setIsCategoryComposerOpen(false);
  }

  function clearCategory() {
    setCategory('');
    setCategoryDraft('');
    setIsCategoryComposerOpen(false);
  }

  function upsertRubric(rubric: Rubric) {
    setRubrics((prev) => {
      const existingIndex = prev.findIndex((r) => r.id === rubric.id);
      if (existingIndex === -1) return [rubric, ...prev];
      const copy = [...prev];
      copy[existingIndex] = rubric;
      return copy;
    });
  }

  function handleQuickRubricCreated(rubric: Rubric) {
    upsertRubric(rubric);
    setRubricApplyId(String(rubric.id));

    if (isRubricEnabled) {
      const targetIndices =
        selectedQuestionIndices.length > 0
          ? selectedQuestionIndices
          : [selectedQuestionIndex];
      applyRubricToIndices(targetIndices, rubric.id);
      toast.success('Rubric attached to active/selected question(s).');
    }
  }

  function openRubricPreview(rubricId: number | null | undefined) {
    if (rubricId == null) return;
    setPreviewRubricId(rubricId);
    setIsRubricPreviewOpen(true);
  }

  function handleQuickRubricSaved(rubric: Rubric) {
    upsertRubric(rubric);
    toast.success(`Rubric "${rubric.title}" is up to date in this builder.`);
  }

  function openInlineRubricEditor(rubricId: number | null | undefined) {
    if (rubricId == null) return;
    setQuickEditRubricId(rubricId);
    setIsQuickRubricEditOpen(true);
  }

  function openFullRubricEditor(rubricId?: number | null) {
    const query = searchParams.toString();
    const returnTo = query ? `${pathname}?${query}` : pathname;
    if (rubricId == null) {
      router.push(`/dashboard/rubrics/new?returnTo=${encodeURIComponent(returnTo)}`);
      return;
    }
    router.push(`/dashboard/rubrics/${rubricId}/edit?returnTo=${encodeURIComponent(returnTo)}`);
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

    if (questions.length === 0) {
      setQuestionsError('At least one question is required');
      valid = false;
    } else if (questions.some((q) => !q.prompt.trim())) {
      setQuestionsError('Every question must have a non-empty prompt');
      valid = false;
    } else {
      if (gradingMode === 'AUTO') {
        const hasAnyRubric =
          questionGroups.some((g) => g.rubricId != null) ||
          questions.some((q) => effectiveRubricId(q) != null);
        if (hasAnyRubric) {
          setQuestionsError('AUTO mode does not allow rubric linkage.');
          valid = false;
        } else {
          setQuestionsError(null);
        }
      } else if (gradingMode === 'MANUAL') {
        const missingRubric = questions.find((q) => effectiveRubricId(q) == null);
        if (missingRubric) {
          setQuestionsError(
            'MANUAL mode requires a rubric for every question (directly or via group).',
          );
          valid = false;
        } else {
          setQuestionsError(null);
        }
      } else {
        const invalid = questions.find((q) => {
          const strategy = q.gradingStrategy ?? 'AUTO';
          const hasRubric = effectiveRubricId(q) != null;
          if (strategy === 'MANUAL') return !hasRubric;
          return hasRubric;
        });
        if (invalid) {
          setQuestionsError(
            'HYBRID mode requires rubrics only on MANUAL strategy questions.',
          );
          valid = false;
        } else {
          setQuestionsError(null);
        }
      }
    }

    if (questionGroups.some((g) => !g.name.trim())) {
      setQuestionsError('Question group names cannot be empty.');
      valid = false;
    }

    return valid;
  }

  // -- Submit --

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);

    const payload: AssessmentInput = {
      title: title.trim(),
      category: category.trim() || null,
      gradingMode: gradingMode as GradingMode,
      scoringPolicy,
      questions: questions.map((q) => ({
        ...q,
        type: normalizeQuestionKind(String(q.type)),
        rubricId: q.rubricId ?? null,
        gradingStrategy:
          gradingMode === 'HYBRID' ? q.gradingStrategy ?? 'AUTO' : undefined,
      })),
      questionGroups: questionGroups.map((g) => ({
        clientKey: g.clientKey,
        name: g.name.trim(),
        rubricId: g.rubricId ?? null,
      })),
    };

    try {
      if (mode === 'create') {
        const created = await createAssessment(payload);
        toast.success('Assessment created');
        router.push(`/dashboard/assessments/${created.id}`);
      } else {
        await updateAssessment(assessmentId!, payload);
        toast.success('Assessment updated');
        router.replace(`/dashboard/assessments/${assessmentId}`);
        router.refresh();
      }
    } catch (err: unknown) {
      if (mode === 'edit' && getStatusCode(err) === 409) {
        toast.error(
          'This assessment is referenced by assignments and cannot be modified',
        );
      } else {
        toast.error(toErrorMessage(err, 'Failed to save assessment'));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleCancel() {
    if (mode === 'edit' && assessmentId) {
      router.push(`/dashboard/assessments/${assessmentId}`);
    } else {
      router.push('/dashboard/assessments');
    }
  }

  // -- Derived UI state --

  const selectedQuestion = questions[selectedQuestionIndex];
  const selectedCount = selectedQuestionIndices.length;
  const activeSelectionCount = selectedCount > 0 ? selectedCount : 1;
  const ungroupedCount = questions.filter((q) => !q.groupClientKey).length;
  const selectedAssignGroup =
    assignGroupKey !== '__NONE__'
      ? questionGroups.find((group) => group.clientKey === assignGroupKey) ?? null
      : null;
  const selectedGroup = selectedQuestion?.groupClientKey
    ? groupByKey.get(selectedQuestion.groupClientKey)
    : null;
  const selectedEffectiveRubricId = selectedQuestion
    ? effectiveRubricId(selectedQuestion)
    : null;
  const selectedEffectiveRubricName =
    selectedEffectiveRubricId != null
      ? rubricById.get(selectedEffectiveRubricId)?.title ?? 'Rubric unavailable'
      : null;

  const selectedManualCount = useMemo(() => {
    return selectedQuestionIndices.filter((idx) => {
      const question = questions[idx];
      return question ? isManualQuestion(question, gradingMode) : false;
    }).length;
  }, [selectedQuestionIndices, questions, gradingMode]);

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
      {/* Metadata */}
      <div className="rounded-sm border border-border bg-card p-6 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-foreground">Assessment Details</h2>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowTips((v) => !v)}
          >
            {showTips ? 'Hide Tips' : 'Show Tips'}
          </Button>
        </div>

        {showTips && (
          <div className="rounded border border-border bg-muted/40 p-3 text-xs text-muted-foreground space-y-1">
            <p>Use MANUAL when every question should be rubric-graded.</p>
            <p>Use HYBRID to mix AUTO and MANUAL questions with per-question strategy.</p>
            <p>AUTO mode disables rubric attachment completely.</p>
            <p>Completion scoring awards 100 when a student submits (participation credit).</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <div className="space-y-2 lg:col-span-2">
            <div className="flex items-center gap-1.5">
              <Label htmlFor="title">Title</Label>
              <HelpTip text="Clear name for this assessment template (for example: Week 2 Reading Check)." />
            </div>
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
            <div className="flex items-center gap-1.5">
              <Label htmlFor="gradingMode">Grading Mode</Label>
              <HelpTip text="Only AUTO, MANUAL, and HYBRID are supported in this builder. Rubrics are available in MANUAL and HYBRID." />
            </div>
            <Select
              value={gradingMode}
              onValueChange={(v) => setGradingMode(v as BuilderGradingMode)}
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

          <div className="space-y-2">
            <div className="flex items-center gap-1.5">
              <Label htmlFor="scoringPolicy">Scoring Policy</Label>
              <HelpTip text="Standard uses normal point scoring. Completion gives full credit (100) once submitted." />
            </div>
            <Select
              value={scoringPolicy}
              onValueChange={(v) => setScoringPolicy(v as ScoringPolicy)}
            >
              <SelectTrigger id="scoringPolicy">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SCORING_POLICIES.map((policy) => (
                  <SelectItem key={policy.value} value={policy.value}>
                    {policy.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-1.5">
            <Label>Category</Label>
            <HelpTip text="Optional tag to organize assessments. Click + to add or change it, or pick from your existing category bank." />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {category ? (
              <span className="inline-flex items-center rounded-full border border-border bg-muted px-3 py-1 text-xs font-medium text-foreground">
                {category}
              </span>
            ) : (
              <span className="text-xs text-muted-foreground">No category tag set.</span>
            )}

            {!isCategoryComposerOpen && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={openCategoryComposer}
              >
                <Plus className="mr-1 h-3.5 w-3.5" />
                {category ? 'Change' : 'Add Category'}
              </Button>
            )}

            {category && !isCategoryComposerOpen && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={clearCategory}
              >
                Clear
              </Button>
            )}
          </div>

          {isCategoryComposerOpen && (
            <div className="rounded-sm border border-border bg-muted/30 p-2.5 space-y-2 max-w-2xl">
              <div className="flex flex-wrap items-center gap-1.5">
                <Input
                  id="category-composer"
                  placeholder="Type a category..."
                  className="h-8 w-[220px] sm:w-[280px] md:w-[320px]"
                  value={categoryDraft}
                  onChange={(e) => setCategoryDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      applyCategoryDraft();
                    }
                    if (e.key === 'Escape') {
                      e.preventDefault();
                      cancelCategoryComposer();
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 px-2 text-xs"
                  onClick={applyCategoryDraft}
                  disabled={!categoryDraft.trim()}
                >
                  Set Tag
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2 text-xs"
                  onClick={cancelCategoryComposer}
                >
                  Cancel
                </Button>
              </div>

              {categoryOptions.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    Category bank
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {categoryOptions.slice(0, 16).map((option) => (
                      <Button
                        key={option}
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-6 px-2 text-[11px]"
                        onClick={() => chooseCategoryFromBank(option)}
                      >
                        {option}
                      </Button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[300px_minmax(0,1fr)_360px] gap-4 items-start">
          {/* Left: Outline + selection */}
          <aside className="rounded-sm border border-border bg-card p-4 space-y-4 xl:sticky xl:top-4 max-h-[calc(100vh-180px)] overflow-y-auto">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <h3 className="text-sm font-semibold text-foreground">
                  Questions ({questions.length})
                </h3>
                <HelpTip text="Left side is your outline. Click a question to edit it in the center panel." />
              </div>
              <Button type="button" variant="outline" size="sm" onClick={addQuestion}>
                <Plus className="mr-1 h-4 w-4" /> Add
              </Button>
            </div>

            {questionsError && <p className="text-xs text-destructive">{questionsError}</p>}

            <div className="space-y-2">
              {questions.map((q, idx) => {
                const manual = isManualQuestion(q, gradingMode);
                const effRubric = effectiveRubricId(q);
                const groupName = q.groupClientKey
                  ? groupByKey.get(q.groupClientKey)?.name ?? 'Unknown'
                  : 'None';
                const gradingLabel =
                  gradingMode === 'HYBRID'
                    ? (q.gradingStrategy ?? 'AUTO')
                    : (manual ? 'MANUAL' : 'AUTO');
                const rubricLabel = effRubric
                  ? rubricById.get(effRubric)?.title ?? 'Unavailable'
                  : 'None';
                return (
                  <button
                    key={`q-${idx}`}
                    type="button"
                    data-question-row="true"
                    className={`relative w-full rounded border py-2 pr-2 text-left transition-colors ${
                      idx === selectedQuestionIndex
                        ? 'border-primary bg-accent'
                        : 'border-border hover:bg-accent/50'
                    } ${
                      dragOverQuestionIndex === idx && draggingQuestionIndex !== idx
                        ? 'ring-1 ring-primary ring-offset-1 ring-offset-background'
                        : ''
                    }`}
                    onClick={() => setSelectedQuestionIndex(idx)}
                    onDragOver={(e) => {
                      e.preventDefault();
                      if (draggingQuestionIndex !== null && draggingQuestionIndex !== idx) {
                        setDragOverQuestionIndex(idx);
                      }
                    }}
                    onDrop={(e) => {
                      e.preventDefault();
                      if (draggingQuestionIndex !== null) {
                        moveQuestion(draggingQuestionIndex, idx);
                      }
                      setDraggingQuestionIndex(null);
                      setDragOverQuestionIndex(null);
                    }}
                    onDragEnd={() => {
                      setDraggingQuestionIndex(null);
                      setDragOverQuestionIndex(null);
                    }}
                  >
                    <span
                      role="button"
                      tabIndex={0}
                      draggable
                      aria-label={`Drag question ${idx + 1}`}
                      className="absolute inset-y-0 left-0 inline-flex w-7 cursor-grab items-center justify-center rounded-l border-r border-border bg-muted/30 text-muted-foreground hover:text-foreground active:cursor-grabbing"
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          e.stopPropagation();
                        }
                      }}
                      onDragStart={(e) => {
                        e.stopPropagation();
                        const row = e.currentTarget.closest(
                          '[data-question-row="true"]',
                        ) as HTMLElement | null;
                        if (row) {
                          e.dataTransfer.setDragImage(row, 24, 18);
                        }
                        setDraggingQuestionIndex(idx);
                        setDragOverQuestionIndex(idx);
                        e.dataTransfer.effectAllowed = 'move';
                        e.dataTransfer.setData('text/plain', String(idx));
                      }}
                      onDragEnd={(e) => {
                        e.stopPropagation();
                        setDraggingQuestionIndex(null);
                        setDragOverQuestionIndex(null);
                      }}
                    >
                      <GripVertical className="h-3.5 w-3.5" />
                    </span>

                    <div className="flex items-start gap-2 pl-9">
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={selectedQuestionIndices.includes(idx)}
                        onChange={(e) => {
                          e.stopPropagation();
                          toggleSelectedQuestion(idx, e.target.checked);
                        }}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-foreground truncate">
                          Q{idx + 1}. {q.prompt.trim() || 'Untitled question'}
                        </p>
                        <div className="mt-1 text-[11px] text-muted-foreground leading-relaxed">
                          <span>Type: {formatQuestionKind(q.type)}</span>
                          <span className="mx-1">•</span>
                          <span>Grading: {gradingLabel}</span>
                          <span className="mx-1">•</span>
                          <span>Group: {groupName}</span>
                        </div>
                        <div className="text-[11px] font-medium text-foreground/80">
                          Rubric: {rubricLabel}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="border-t border-border pt-3 space-y-2">
              <p className="text-[11px] text-muted-foreground">
                Drag by the handle to reorder questions.
              </p>
              <p className="text-xs text-muted-foreground">
                Selected: {selectedCount}
                {selectedCount > 0 && gradingMode === 'HYBRID'
                  ? ` (${selectedManualCount} manual)`
                  : ''}
              </p>
            </div>
          </aside>

          {/* Center: Selected question editor */}
          <QuestionEditor
            selectedQuestionIndex={selectedQuestionIndex}
            selectedQuestion={selectedQuestion}
            questions={questions}
            gradingMode={gradingMode}
            questionGroups={questionGroups}
            selectedEffectiveRubricName={selectedEffectiveRubricName}
            selectedGroupName={selectedGroup?.name ?? null}
            rubricSource={
              selectedQuestion?.rubricId != null
                ? 'Question'
                : selectedEffectiveRubricId != null
                  ? 'Group'
                  : 'N/A'
            }
            onQuestionChange={handleQuestionChange}
            onQuestionRemove={handleQuestionRemove}
            onMoveUp={handleMoveUp}
            onMoveDown={handleMoveDown}
          />

          {/* Right: Rubric and group panel */}
          <QuestionGroupPanel
            isRubricEnabled={isRubricEnabled}
            isRubricsLoading={isRubricsLoading}
            rubrics={rubrics}
            rubricApplyId={rubricApplyId}
            onRubricApplyIdChange={setRubricApplyId}
            onApplyRubricToSelected={applyRubricToSelectedQuestions}
            onOpenQuickRubric={() => setIsQuickRubricOpen(true)}
            onOpenInlineRubricEditor={openInlineRubricEditor}
            onOpenRubricPreview={openRubricPreview}
            showTips={showTips}
            questionGroups={questionGroups}
            newGroupName={newGroupName}
            onNewGroupNameChange={setNewGroupName}
            onCreateGroup={createGroupFromInput}
            ungroupedCount={ungroupedCount}
            activeSelectionCount={activeSelectionCount}
            assignGroupKey={assignGroupKey}
            onAssignGroupKeyChange={setAssignGroupKey}
            selectedAssignGroup={selectedAssignGroup}
            questionCountByGroupKey={questionCountByGroupKey}
            rubricById={rubricById}
            onUpdateQuestionGroup={updateQuestionGroup}
            onRemoveQuestionGroup={removeQuestionGroup}
            onAssignGroupToSelected={assignGroupToSelected}
          />
        </div>

      {/* Action buttons and rubric drawers */}
      <AssessmentActionBar
        mode={mode}
        isSubmitting={isSubmitting}
        onCancel={handleCancel}
        isQuickRubricOpen={isQuickRubricOpen}
        onQuickRubricOpenChange={setIsQuickRubricOpen}
        onQuickRubricCreated={handleQuickRubricCreated}
        isQuickRubricEditOpen={isQuickRubricEditOpen}
        onQuickRubricEditOpenChange={setIsQuickRubricEditOpen}
        quickEditRubricId={quickEditRubricId}
        onQuickRubricSaved={handleQuickRubricSaved}
        isRubricPreviewOpen={isRubricPreviewOpen}
        onRubricPreviewOpenChange={setIsRubricPreviewOpen}
        previewRubricId={previewRubricId}
        onOpenInlineRubricEditor={openInlineRubricEditor}
        onOpenFullRubricEditor={openFullRubricEditor}
      />
    </form>
  );
}
