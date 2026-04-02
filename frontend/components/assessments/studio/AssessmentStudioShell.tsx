'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

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
import { toErrorMessage, cn } from '@/lib/utils';

import AssessmentStudioHeader from './AssessmentStudioHeader';
import StructureRail from './StructureRail';
import QuestionStudio from './QuestionStudio';
import ValidationRail from './ValidationRail';
import AssessmentActionBar from '../AssessmentActionBar';

// -- Error handling --

function getStatusCode(error: unknown): number | undefined {
  return (error as { response?: { status?: number } }).response?.status;
}

// -- Constants --

type BuilderGradingMode = 'AUTO' | 'MANUAL' | 'HYBRID';

function emptyMcqQuestion(): QuestionInput {
  return {
    type: 'MULTIPLE_CHOICE' as QuestionKind,
    prompt: '',
    maxPoints: 0,
    data: { choices: [{ prompt: '', score: 0 }], selectAll: false },
    gradingStrategy: 'AUTO',
  };
}

function makeGroupKey(nextIndex: number): string {
  return `group-${Date.now()}-${nextIndex}`;
}

function normalizeBuilderMode(mode: GradingMode): BuilderGradingMode {
  if (mode === 'AUTO' || mode === 'MANUAL' || mode === 'HYBRID') return mode;
  return 'MANUAL';
}

function normalizeQuestionKind(kind: string): QuestionKind {
  if (
    kind === 'MULTIPLE_CHOICE' ||
    kind === 'SHORT_ANSWER' ||
    kind === 'NUMBER_SCALE' ||
    kind === 'MOOD_METER'
  ) {
    return kind;
  }
  return 'SHORT_ANSWER';
}

// -- Props --

type AssessmentStudioShellProps = {
  mode: 'create' | 'edit';
  assessmentId?: number;
};

export default function AssessmentStudioShell({
  mode,
  assessmentId,
}: AssessmentStudioShellProps) {
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
  const [questions, setQuestions] = useState<QuestionInput[]>([
    emptyMcqQuestion(),
  ]);
  const [questionGroups, setQuestionGroups] = useState<QuestionGroupInput[]>(
    [],
  );
  const [categoryOptions, setCategoryOptions] = useState<string[]>([]);

  // Selection / editor state
  const [selectedQuestionIndex, setSelectedQuestionIndex] = useState(0);
  const [selectedQuestionIndices, setSelectedQuestionIndices] = useState<
    number[]
  >([]);
  const [assignGroupKey, setAssignGroupKey] = useState('__NONE__');
  const [rubricApplyId, setRubricApplyId] = useState('__NONE__');
  const [newGroupName, setNewGroupName] = useState('');
  const [draggingQuestionIndex, setDraggingQuestionIndex] = useState<
    number | null
  >(null);
  const [dragOverQuestionIndex, setDragOverQuestionIndex] = useState<
    number | null
  >(null);

  // Rubric options
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [isRubricsLoading, setIsRubricsLoading] = useState(true);
  const [isQuickRubricOpen, setIsQuickRubricOpen] = useState(false);
  const [isQuickRubricEditOpen, setIsQuickRubricEditOpen] = useState(false);
  const [quickEditRubricId, setQuickEditRubricId] = useState<number | null>(
    null,
  );
  const [isRubricPreviewOpen, setIsRubricPreviewOpen] = useState(false);
  const [previewRubricId, setPreviewRubricId] = useState<number | null>(null);

  // UI state
  const [titleError, setTitleError] = useState<string | null>(null);
  const [questionsError, setQuestionsError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(mode === 'edit');
  const [assessmentStatus, setAssessmentStatus] = useState<string>('ACTIVE');

  // Mobile tab state
  const [mobileView, setMobileView] = useState<
    'structure' | 'editor' | 'settings'
  >('editor');

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

  function isManualQuestion(
    q: QuestionInput,
    modeValue: BuilderGradingMode,
  ): boolean {
    if (modeValue === 'MANUAL') return true;
    if (modeValue === 'HYBRID') {
      return (q.gradingStrategy ?? 'AUTO') === 'MANUAL';
    }
    return false;
  }

  function effectiveRubricId(q: QuestionInput): number | null {
    if (q.rubricId != null) return q.rubricId;
    if (!q.groupClientKey) return null;
    const group = questionGroups.find(
      (g) => g.clientKey === q.groupClientKey,
    );
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
        setAssessmentStatus(a.status ?? 'ACTIVE');

        const mappedGroups: QuestionGroupInput[] = (
          a.questionGroups ?? []
        ).map((group, index) => ({
          clientKey: `group-${group.id}-${index}`,
          name: group.name,
          rubricId: group.rubricId,
        }));
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

  const handleQuestionChange = useCallback(
    (index: number, updated: QuestionInput) => {
      setQuestions((prev) => prev.map((q, i) => (i === index ? updated : q)));
    },
    [],
  );

  const handleQuestionRemove = useCallback(
    (index: number) => {
      setQuestions((prev) => {
        const next = prev.filter((_, i) => i !== index);
        if (next.length === 0) {
          return [emptyMcqQuestion()];
        }
        return next;
      });

      setSelectedQuestionIndices((prev) =>
        prev
          .filter((i) => i !== index)
          .map((i) => (i > index ? i - 1 : i)),
      );

      setSelectedQuestionIndex((prev) => {
        if (prev === index) {
          if (questions.length <= 1) return 0;
          return index === questions.length - 1 ? index - 1 : index;
        }
        if (prev > index) return prev - 1;
        return prev;
      });
    },
    [questions.length],
  );

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

  const handleMoveDown = useCallback(
    (index: number) => {
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
    },
    [questions.length],
  );

  function addQuestion() {
    setQuestions((prev) => {
      const next = [...prev, emptyMcqQuestion()];
      setSelectedQuestionIndex(next.length - 1);
      return next;
    });
  }

  function remapIndexAfterMove(
    index: number,
    from: number,
    to: number,
  ): number {
    if (index === from) return to;
    if (from < to && index > from && index <= to) return index - 1;
    if (from > to && index >= to && index < from) return index + 1;
    return index;
  }

  function moveQuestion(from: number, to: number) {
    if (
      from === to ||
      from < 0 ||
      to < 0 ||
      from >= questions.length ||
      to >= questions.length
    ) {
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
    setSelectedQuestionIndex((prev) =>
      remapIndexAfterMove(prev, from, to),
    );
  }

  function duplicateQuestion(index: number) {
    const q = questions[index];
    if (!q) return;
    const duplicated: QuestionInput = {
      ...q,
      prompt: `${q.prompt} (Copy)`,
      data: q.data ? { ...q.data } : undefined,
    };
    setQuestions((prev) => {
      const next = [...prev, duplicated];
      setSelectedQuestionIndex(next.length - 1);
      return next;
    });
  }

  function addQuestionGroup(preferredName?: string) {
    const nextIndex = questionGroups.length + 1;
    const clientKey = makeGroupKey(nextIndex);
    const name = preferredName?.trim() || `Group ${nextIndex}`;
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
    setQuestionGroups((prev) =>
      prev.filter((g) => g.clientKey !== clientKey),
    );
    setQuestions((prev) =>
      prev.map((q) =>
        q.groupClientKey === clientKey
          ? { ...q, groupClientKey: undefined }
          : q,
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
          groupClientKey:
            assignGroupKey === '__NONE__' ? undefined : assignGroupKey,
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

    const rubricId =
      rubricApplyId === '__NONE__' ? null : Number(rubricApplyId);

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

  function applyCategoryDraft() {
    const next = categoryDraft.trim();
    setCategory(next);
    setCategoryDraft(next);
    setIsCategoryComposerOpen(false);
  }

  function cancelCategoryComposer() {
    setCategoryDraft(category);
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
      router.push(
        `/dashboard/rubrics/new?returnTo=${encodeURIComponent(returnTo)}`,
      );
      return;
    }
    router.push(
      `/dashboard/rubrics/${rubricId}/edit?returnTo=${encodeURIComponent(returnTo)}`,
    );
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
        const missingRubric = questions.find(
          (q) => effectiveRubricId(q) == null,
        );
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

  async function handleSubmit(e?: React.FormEvent) {
    if (e) e.preventDefault();
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
          gradingMode === 'HYBRID' ? (q.gradingStrategy ?? 'AUTO') : undefined,
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
  const ungroupedCount = questions.filter(
    (q) => !q.groupClientKey,
  ).length;
  const selectedAssignGroup =
    assignGroupKey !== '__NONE__'
      ? questionGroups.find(
          (group) => group.clientKey === assignGroupKey,
        ) ?? null
      : null;
  const selectedGroup = selectedQuestion?.groupClientKey
    ? groupByKey.get(selectedQuestion.groupClientKey)
    : null;
  const selectedEffectiveRubricId = selectedQuestion
    ? effectiveRubricId(selectedQuestion)
    : null;
  const selectedEffectiveRubricName =
    selectedEffectiveRubricId != null
      ? (rubricById.get(selectedEffectiveRubricId)?.title ??
        'Rubric unavailable')
      : null;

  // -- Render --

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col h-[calc(100vh-64px)] overflow-hidden"
    >
      {/* Top header bar */}
      <AssessmentStudioHeader
        title={title}
        onTitleChange={(t) => {
          setTitle(t);
          if (titleError) setTitleError(null);
        }}
        titleError={titleError}
        status={assessmentStatus}
        mode={mode}
        isSubmitting={isSubmitting}
        onSave={() => void handleSubmit()}
        onCancel={handleCancel}
      />

      {/* Mobile tab bar */}
      <div className="lg:hidden flex border-b border-border bg-muted/30">
        {(
          [
            { key: 'structure', label: 'Structure' },
            { key: 'editor', label: 'Editor' },
            { key: 'settings', label: 'Settings' },
          ] as const
        ).map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setMobileView(tab.key)}
            className={cn(
              'flex-1 py-2.5 text-[10px] font-bold uppercase tracking-widest transition-colors',
              mobileView === tab.key
                ? 'text-foreground border-b-2 border-primary bg-card'
                : 'text-muted-foreground',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main 3-column layout */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Rail */}
        <aside
          className={cn(
            'w-[280px] border-r border-border bg-muted/30 flex flex-col shrink-0 transition-transform duration-200',
            'max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:z-20 max-lg:w-full max-lg:bg-background',
            mobileView === 'structure'
              ? 'max-lg:translate-x-0'
              : 'max-lg:-translate-x-full lg:translate-x-0',
          )}
        >
          <StructureRail
            questions={questions}
            questionGroups={questionGroups}
            selectedIndex={selectedQuestionIndex}
            onSelectQuestion={(idx) => {
              setSelectedQuestionIndex(idx);
              setMobileView('editor');
            }}
            onAddQuestion={addQuestion}
            onAddGroup={() => addQuestionGroup()}
            draggingQuestionIndex={draggingQuestionIndex}
            dragOverQuestionIndex={dragOverQuestionIndex}
            onDragStart={(idx) => {
              setDraggingQuestionIndex(idx);
              setDragOverQuestionIndex(idx);
            }}
            onDragOver={(idx) => setDragOverQuestionIndex(idx)}
            onDrop={(from, to) => moveQuestion(from, to)}
            onDragEnd={() => {
              setDraggingQuestionIndex(null);
              setDragOverQuestionIndex(null);
            }}
            groupByKey={groupByKey}
          />
        </aside>

        {/* Center editor */}
        <main
          className={cn(
            'flex-1 bg-background overflow-y-auto transition-opacity duration-200',
            mobileView !== 'editor' && 'max-lg:hidden',
          )}
        >
          <div className="max-w-4xl mx-auto py-6 lg:py-10 px-4 lg:px-8">
            <QuestionStudio
              question={selectedQuestion}
              questionIndex={selectedQuestionIndex}
              questionsCount={questions.length}
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
              onChange={(updated) =>
                handleQuestionChange(selectedQuestionIndex, updated)
              }
              onRemove={() => handleQuestionRemove(selectedQuestionIndex)}
              onDuplicate={() => duplicateQuestion(selectedQuestionIndex)}
              onMoveUp={
                selectedQuestionIndex === 0
                  ? null
                  : () => handleMoveUp(selectedQuestionIndex)
              }
              onMoveDown={
                selectedQuestionIndex === questions.length - 1
                  ? null
                  : () => handleMoveDown(selectedQuestionIndex)
              }
              onAddQuestion={addQuestion}
            />
          </div>
        </main>

        {/* Right Rail */}
        <aside
          className={cn(
            'w-[280px] border-l border-border bg-muted/30 shrink-0 overflow-hidden transition-transform duration-200',
            'max-lg:fixed max-lg:inset-y-0 max-lg:right-0 max-lg:z-20 max-lg:w-full max-lg:bg-background',
            mobileView === 'settings'
              ? 'max-lg:translate-x-0'
              : 'max-lg:translate-x-full lg:translate-x-0',
          )}
        >
          <ValidationRail
            gradingMode={gradingMode}
            onGradingModeChange={setGradingMode}
            scoringPolicy={scoringPolicy}
            onScoringPolicyChange={setScoringPolicy}
            activeQuestion={selectedQuestion}
            activeQuestionIndex={selectedQuestionIndex}
            questions={questions}
            questionsError={questionsError}
            onNavigateToQuestion={(idx) => {
              setSelectedQuestionIndex(idx);
              setMobileView('editor');
            }}
            isRubricEnabled={isRubricEnabled}
            isRubricsLoading={isRubricsLoading}
            rubrics={rubrics}
            rubricApplyId={rubricApplyId}
            onRubricApplyIdChange={setRubricApplyId}
            onApplyRubricToSelected={applyRubricToSelectedQuestions}
            onOpenQuickRubric={() => setIsQuickRubricOpen(true)}
            onOpenInlineRubricEditor={openInlineRubricEditor}
            onOpenRubricPreview={openRubricPreview}
            questionGroups={questionGroups}
            newGroupName={newGroupName}
            onNewGroupNameChange={setNewGroupName}
            onCreateGroup={createGroupFromInput}
            assignGroupKey={assignGroupKey}
            onAssignGroupKeyChange={setAssignGroupKey}
            selectedAssignGroup={selectedAssignGroup}
            questionCountByGroupKey={questionCountByGroupKey}
            rubricById={rubricById}
            onUpdateQuestionGroup={updateQuestionGroup}
            onRemoveQuestionGroup={removeQuestionGroup}
            onAssignGroupToSelected={assignGroupToSelected}
            category={category}
            onCategoryChange={setCategory}
            categoryOptions={categoryOptions}
            isCategoryComposerOpen={isCategoryComposerOpen}
            onCategoryComposerOpenChange={setIsCategoryComposerOpen}
            categoryDraft={categoryDraft}
            onCategoryDraftChange={setCategoryDraft}
            onApplyCategoryDraft={applyCategoryDraft}
            onCancelCategoryComposer={cancelCategoryComposer}
            onChooseCategoryFromBank={chooseCategoryFromBank}
            onClearCategory={clearCategory}
          />
        </aside>
      </div>

      {/* Hidden action bar with rubric drawers */}
      <div className="hidden">
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
      </div>
    </form>
  );
}
