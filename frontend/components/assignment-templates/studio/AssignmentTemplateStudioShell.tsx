'use client';

import { useState, useEffect, useCallback, useMemo, useDeferredValue, useRef } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import {
  type AssignmentTemplate,
  type AssignmentTemplateInput,
  type QuestionInput,
  type QuestionImage,
  type GradingMode,
  type ScoringPolicy,
  type SubmissionMode,
  type QuestionKind,
  type QuestionGroupInput,
  getAssignmentTemplate,
  createDraft,
  listAssignmentTemplates,
  updateAssignmentTemplate,
  deleteAssignmentTemplate,
  publishAssignmentTemplate,
  uploadQuestionImage,
  deleteQuestionImage,
} from '@/lib/assignment-template-api';
import { listRubrics, type Rubric } from '@/lib/rubric-api';
import { toErrorMessage, cn } from '@/lib/utils';

import AssignmentTemplateStudioHeader from './AssignmentTemplateStudioHeader';
import StructureRail from './StructureRail';
import QuestionStudio from './QuestionStudio';
import ValidationRail from './ValidationRail';
import AssignmentTemplateActionBar from '../AssignmentTemplateActionBar';
import {
  buildStudioValidationIssues,
  type StudioValidationIssue,
} from './validation';
import { syncDerivedQuestionPoints } from './scoring';

// -- Error handling --

function getStatusCode(error: unknown): number | undefined {
  return (error as { response?: { status?: number } }).response?.status;
}

// -- Constants --

type BuilderGradingMode = 'AUTO' | 'MANUAL' | 'HYBRID';

function emptyMcqQuestion(): QuestionInput {
  return syncDerivedQuestionPoints({
    type: 'MULTIPLE_CHOICE' as QuestionKind,
    prompt: '',
    maxPoints: 0,
    data: { choices: [{ prompt: '', score: 0 }], selectAll: false },
    gradingStrategy: 'AUTO',
  });
}

function makeGroupKey(nextIndex: number): string {
  return `group-${Date.now()}-${nextIndex}`;
}

function remapQuestionIdMapAfterMove(
  current: Map<number, number>,
  from: number,
  to: number,
): Map<number, number> {
  const next = new Map<number, number>();
  current.forEach((questionId, index) => {
    let remappedIndex = index;
    if (index === from) {
      remappedIndex = to;
    } else if (from < to && index > from && index <= to) {
      remappedIndex = index - 1;
    } else if (from > to && index >= to && index < from) {
      remappedIndex = index + 1;
    }
    next.set(remappedIndex, questionId);
  });
  return next;
}

function remapQuestionIdMapAfterRemoval(
  current: Map<number, number>,
  removedIndex: number,
): Map<number, number> {
  const next = new Map<number, number>();
  current.forEach((questionId, index) => {
    if (index === removedIndex) return;
    next.set(index > removedIndex ? index - 1 : index, questionId);
  });
  return next;
}

function remapQuestionIdMapAfterAppend(
  current: Map<number, number>,
  nextLength: number,
): Map<number, number> {
  const next = new Map(current);
  next.delete(nextLength - 1);
  return next;
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
  // Legacy FILE_UPLOAD questions fall back to SHORT_ANSWER
  return 'SHORT_ANSWER';
}

// -- Props --

type AssignmentTemplateStudioShellProps = {
  mode: 'create' | 'edit';
  assignmentTemplateId?: number;
};

export default function AssignmentTemplateStudioShell({
  mode,
  assignmentTemplateId,
}: AssignmentTemplateStudioShellProps) {
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
  const [submissionMode, setSubmissionModeRaw] = useState<SubmissionMode>('DIGITAL');
  const setSubmissionMode = useCallback((mode: SubmissionMode) => {
    setSubmissionModeRaw(mode);
    if (mode === 'UPLOAD_ONLY' || mode === 'DIGITAL_WITH_UPLOAD') {
      setGradingMode('MANUAL');
    }
  }, []);
  const [assignmentTemplateRubricId, setAssignmentTemplateRubricId] = useState<number | null>(
    null,
  );
  const [questions, setQuestions] = useState<QuestionInput[]>([
    emptyMcqQuestion(),
  ]);
  const [questionGroups, setQuestionGroups] = useState<QuestionGroupInput[]>(
    [],
  );
  const [categoryOptions, setCategoryOptions] = useState<string[]>([]);

  // Selection / editor state
  const [selectedQuestionIndex, setSelectedQuestionIndex] = useState(0);
  const [assignGroupKey, setAssignGroupKey] = useState('__NONE__');
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
  const [isLoading, setIsLoading] = useState(true);
  const [assignmentTemplateStatus, setAssignmentTemplateStatus] = useState<string>(
    mode === 'create' ? 'DRAFT' : 'ACTIVE',
  );
  // The resolved backend assignment template ID (set after draft creation or edit load)
  const [resolvedId, setResolvedId] = useState<number | undefined>(assignmentTemplateId);
  // Maps frontend question array index → backend question ID
  const [questionIdMap, setQuestionIdMap] = useState<Map<number, number>>(
    new Map(),
  );
  const [activeValidationIssue, setActiveValidationIssue] =
    useState<StudioValidationIssue | null>(null);
  const [validationFocusSignal, setValidationFocusSignal] = useState(0);

  // Autosave state
  type SaveState = 'idle' | 'saving' | 'saved' | 'error';
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [isPublishing, setIsPublishing] = useState(false);
  const autosaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autosavePrimedRef = useRef(false);
  const isDraft = assignmentTemplateStatus === 'DRAFT';

  // Mobile tab state
  const [mobileView, setMobileView] = useState<
    'structure' | 'editor' | 'settings'
  >('editor');

  const deferredTitle = useDeferredValue(title);
  const deferredAssignmentTemplateRubricId = useDeferredValue(assignmentTemplateRubricId);
  const deferredQuestions = useDeferredValue(questions);
  const deferredQuestionGroups = useDeferredValue(questionGroups);

  const clearValidationAttention = useCallback(() => {
    setActiveValidationIssue(null);
    setTitleError(null);
    setQuestionsError(null);
  }, []);

  const rubricById = useMemo(() => {
    const map = new Map<number, Rubric>();
    for (const rubric of rubrics) {
      map.set(rubric.id, rubric);
    }
    return map;
  }, [rubrics]);

  const groupByKey = useMemo(() => {
    const map = new Map<string, QuestionGroupInput>();
    for (const group of deferredQuestionGroups) {
      map.set(group.clientKey, group);
    }
    return map;
  }, [deferredQuestionGroups]);

  const questionCountByGroupKey = useMemo(() => {
    const map = new Map<string, number>();
    for (const question of deferredQuestions) {
      if (!question.groupClientKey) continue;
      map.set(
        question.groupClientKey,
        (map.get(question.groupClientKey) ?? 0) + 1,
      );
    }
    return map;
  }, [deferredQuestions]);

  const isRubricEnabled = gradingMode !== 'AUTO';
  const hasSpecificRubrics = useMemo(
    () =>
      questionGroups.some((group) => group.rubricId != null) ||
      questions.some((question) => question.rubricId != null),
    [questionGroups, questions],
  );

  const effectiveRubricId = useCallback(
    (q: QuestionInput): number | null => {
      if (q.rubricId != null) return q.rubricId;
      if (q.groupClientKey) {
        const group = questionGroups.find(
          (g) => g.clientKey === q.groupClientKey,
        );
        if (group?.rubricId != null) return group.rubricId;
      }
      return assignmentTemplateRubricId;
    },
    [questionGroups, assignmentTemplateRubricId],
  );

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
        const items = await listAssignmentTemplates();
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

  // -- Load or create draft --

  function applyAssignmentTemplateData(a: AssignmentTemplate) {
    setTitle(a.title);
    setCategory(a.category ?? '');
    setGradingMode(normalizeBuilderMode(a.gradingMode));
    setScoringPolicy(a.scoringPolicy ?? 'STANDARD');
    setSubmissionModeRaw(a.submissionMode ?? 'DIGITAL');
    setAssignmentTemplateRubricId(a.rubricId ?? null);
    setAssignmentTemplateStatus(a.status ?? 'ACTIVE');
    setResolvedId(a.id);

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
          ...syncDerivedQuestionPoints({
            type: normalizeQuestionKind(String(q.type)),
            prompt: q.prompt,
            maxPoints: q.maxPoints,
            data: q.data ?? undefined,
            gradingStrategy: q.gradingStrategy,
            rubricId: q.rubricId,
            groupClientKey:
              q.groupId != null ? groupKeyById.get(q.groupId) : undefined,
            questionImage: q.image ?? null,
          }),
        })),
      );
      const idMap = new Map<number, number>();
      a.questions.forEach((q, idx) => idMap.set(idx, q.id));
      setQuestionIdMap(idMap);

      setSelectedQuestionIndex(0);
      const firstQuestionGroupKey =
        a.questions[0].groupId != null
          ? groupKeyById.get(a.questions[0].groupId) ?? '__NONE__'
          : '__NONE__';
      setAssignGroupKey(firstQuestionGroupKey);
    } else {
      setQuestions([emptyMcqQuestion()]);
      setSelectedQuestionIndex(0);
      setAssignGroupKey('__NONE__');
      setQuestionIdMap(new Map());
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        if (mode === 'edit' && assignmentTemplateId) {
          // Load existing assignment template
          const a = await getAssignmentTemplate(assignmentTemplateId);
          if (cancelled) return;
          applyAssignmentTemplateData(a);
        } else {
          // Create mode: immediately create a DRAFT
          const a = await createDraftAssignmentTemplate();
          if (cancelled) return;
          applyAssignmentTemplateData(a);
          // Replace URL so browser back works and we don't create another draft
          window.history.replaceState(
            null,
            '',
            `/dashboard/assignment-templates/${a.id}/edit`,
          );
        }
      } catch {
        if (!cancelled) {
          toast.error('Failed to initialize assignment template');
          router.push('/dashboard/assignment-templates');
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void init();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // -- Question array helpers --

  const handleQuestionChange = useCallback(
    (index: number, updated: QuestionInput) => {
      clearValidationAttention();
      const normalized = syncDerivedQuestionPoints(updated);
      setQuestions((prev) => prev.map((q, i) => (i === index ? normalized : q)));
    },
    [clearValidationAttention],
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
      setQuestionIdMap((prev) => remapQuestionIdMapAfterRemoval(prev, index));

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
      setQuestionIdMap((current) =>
        remapQuestionIdMapAfterAppend(current, next.length),
      );
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
    setQuestionIdMap((prev) => remapQuestionIdMapAfterMove(prev, from, to));
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
      questionImage: null,
    };
    setQuestions((prev) => {
      const next = [...prev, duplicated];
      setQuestionIdMap((current) =>
        remapQuestionIdMapAfterAppend(current, next.length),
      );
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

  const handleAssignGroupKeyChange = useCallback(
    (value: string) => {
      setAssignGroupKey(value);

      const nextGroupClientKey = value === '__NONE__' ? undefined : value;
      const question = questions[selectedQuestionIndex];
      if (!question) return;
      if (question.groupClientKey === nextGroupClientKey) return;

      clearValidationAttention();
      setQuestions((prev) =>
        prev.map((q, i) =>
          i === selectedQuestionIndex
            ? { ...q, groupClientKey: nextGroupClientKey }
            : q,
        ),
      );
    },
    [
      clearValidationAttention,
      questions,
      selectedQuestionIndex,
    ],
  );

  const handleUngroupActiveQuestion = useCallback(() => {
    const question = questions[selectedQuestionIndex];
    if (!question?.groupClientKey) return;

    clearValidationAttention();
    setAssignGroupKey('__NONE__');
    setQuestions((prev) =>
      prev.map((q, i) =>
        i === selectedQuestionIndex ? { ...q, groupClientKey: undefined } : q,
      ),
    );
  }, [clearValidationAttention, questions, selectedQuestionIndex]);

  const handleActiveQuestionRubricChange = useCallback((rubricId: number | null) => {
    if (!isRubricEnabled) {
      toast.error('Switch to MANUAL or HYBRID to attach rubrics.');
      return;
    }
    if (assignmentTemplateRubricId != null && rubricId != null) {
      toast.error(
        'Clear the assignment template rubric before applying question-level rubrics.',
      );
      return;
    }

    clearValidationAttention();
    setQuestions((prev) =>
      prev.map((question, index) => {
        if (index !== selectedQuestionIndex) return question;
        const next: QuestionInput = { ...question, rubricId };
        if (gradingMode === 'HYBRID' && rubricId != null) {
          next.gradingStrategy = 'MANUAL';
        }
        return next;
      }),
    );
  }, [
    assignmentTemplateRubricId,
    clearValidationAttention,
    gradingMode,
    isRubricEnabled,
    selectedQuestionIndex,
  ]);

  const handleActiveQuestionPointsChange = useCallback((value: number) => {
    const question = questions[selectedQuestionIndex];
    if (!question || question.type === 'MULTIPLE_CHOICE') return;

    clearValidationAttention();
    const nextPoints = Math.max(0, value);
    setQuestions((prev) =>
      prev.map((current, index) =>
        index === selectedQuestionIndex
          ? { ...current, maxPoints: nextPoints }
          : current,
      ),
    );
  }, [clearValidationAttention, questions, selectedQuestionIndex]);

  const handleActiveQuestionGradingStrategyChange = useCallback((strategy: 'AUTO' | 'MANUAL') => {
    if (gradingMode !== 'HYBRID') return;
    const question = questions[selectedQuestionIndex];
    if (!question) return;

    clearValidationAttention();
    setQuestions((prev) =>
      prev.map((current, index) =>
        index === selectedQuestionIndex
          ? { ...current, gradingStrategy: strategy }
          : current,
      ),
    );
  }, [clearValidationAttention, gradingMode, questions, selectedQuestionIndex]);

  function createGroupFromInput() {
    if (!newGroupName.trim()) {
      toast.error('Enter a group name first.');
      return;
    }
    addQuestionGroup(newGroupName);
    setNewGroupName('');
    toast.success('Group created.');
  }

  const handleAssignmentTemplateRubricChange = useCallback(
    (rubricId: number | null) => {
      if (rubricId != null && hasSpecificRubrics) {
        toast.error(
          'Clear question and group rubrics before setting an assignment template rubric.',
        );
        return;
      }
      setAssignmentTemplateRubricId(rubricId);
    },
    [hasSpecificRubrics],
  );

  const handleUpdateQuestionGroup = useCallback(
    (clientKey: string, patch: Partial<QuestionGroupInput>) => {
      if (patch.rubricId != null && assignmentTemplateRubricId != null) {
        toast.error(
          'Clear the assignment template rubric before applying group rubrics.',
        );
        return;
      }
      updateQuestionGroup(clientKey, patch);
    },
    [assignmentTemplateRubricId],
  );

  // -- Image upload/remove handlers --

  const handleUploadQuestionImage = useCallback(
    async (questionIdx: number, file: File) => {
      if (!resolvedId) {
        toast.error('Assignment template is still initializing. Try again in a moment.');
        throw new Error('No resolved assignment template ID');
      }
      const backendQuestionId = questionIdMap.get(questionIdx);
      if (backendQuestionId == null) {
        // Trigger an autosave first to get question IDs
        toast.error(
          'Saving assignment template to assign question IDs. Please try again.',
        );
        void performAutosave();
        throw new Error('Question has no backend ID yet');
      }
      const result = await uploadQuestionImage(
        resolvedId,
        backendQuestionId,
        file,
      );
      setQuestions((prev) =>
        prev.map((q, i) =>
          i === questionIdx ? { ...q, questionImage: result } : q,
        ),
      );
      toast.success('Image uploaded');
      return {
        id: result.id,
        url: result.url,
        originalFilename: result.originalFilename,
        mimeType: result.mimeType,
        sizeBytes: result.sizeBytes,
      };
    },
    [resolvedId, questionIdMap],
  );

  const handleRemoveQuestionImage = useCallback(
    async (questionIdx: number) => {
      if (!resolvedId) return;
      const backendQuestionId = questionIdMap.get(questionIdx);
      if (backendQuestionId == null) return;

      try {
        await deleteQuestionImage(resolvedId, backendQuestionId);
      } catch {
        toast.error('Failed to remove image');
        return;
      }
      setQuestions((prev) =>
        prev.map((q, i) =>
          i === questionIdx ? { ...q, questionImage: null } : q,
        ),
      );
      toast.success('Image removed');
    },
    [questionIdMap, resolvedId],
  );

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

    if (isRubricEnabled && assignmentTemplateRubricId == null && questions[selectedQuestionIndex]) {
      handleActiveQuestionRubricChange(rubric.id);
      toast.success('Rubric attached to the active question.');
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

  const validationIssues = useMemo(
    () =>
      buildStudioValidationIssues({
        title,
        questions,
        questionGroups,
        gradingMode,
        submissionMode,
        assignmentTemplateRubricId,
        effectiveRubricId,
      }),
    [title, questions, questionGroups, gradingMode, submissionMode, assignmentTemplateRubricId, effectiveRubricId],
  );

  const deferredValidationIssues = useMemo(
    () =>
      buildStudioValidationIssues({
        title: deferredTitle,
        questions: deferredQuestions,
        questionGroups: deferredQuestionGroups,
        gradingMode,
        submissionMode,
        assignmentTemplateRubricId: deferredAssignmentTemplateRubricId,
        effectiveRubricId,
      }),
    [
      deferredTitle,
      deferredQuestions,
      deferredQuestionGroups,
      gradingMode,
      submissionMode,
      deferredAssignmentTemplateRubricId,
      effectiveRubricId,
    ],
  );

  function navigateToIssue(issue: StudioValidationIssue) {
    if (issue.questionIndex != null) {
      setSelectedQuestionIndex(issue.questionIndex);
    }

    if (issue.panel === 'structure') {
      setMobileView('structure');
    } else if (issue.panel === 'settings') {
      setMobileView('settings');
    } else {
      setMobileView('editor');
    }

    setActiveValidationIssue(issue);
    setValidationFocusSignal((prev) => prev + 1);
  }

  // -- Validation --

  function validate(): boolean {
    const titleIssue = validationIssues.find((issue) => issue.section === 'title');
    setTitleError(titleIssue?.detail ?? null);
    setQuestionsError(
      validationIssues.length > 0
        ? 'Review the validation issues before saving this assignment template.'
        : null,
    );

    if (validationIssues.length > 0) {
      navigateToIssue(validationIssues[0]);
      return false;
    }

    return true;
  }

  // -- Build save payload --

  function buildPayload(): AssignmentTemplateInput {
    return {
      title: title.trim() || 'Untitled Assignment Template',
      category: category.trim() || null,
      gradingMode: gradingMode as GradingMode,
      scoringPolicy,
      submissionMode,
      rubricId: assignmentTemplateRubricId,
      questions: questions.map((q) => {
        const imageJson = q.questionImage
          ? JSON.stringify({
              assetId: q.questionImage.id,
              storageKey: q.questionImage.storageKey,
              originalFilename: q.questionImage.originalFilename,
              mimeType: q.questionImage.mimeType,
              sizeBytes: q.questionImage.sizeBytes,
            })
          : null;

        return {
          type: normalizeQuestionKind(String(q.type)),
          prompt: q.prompt,
          maxPoints: syncDerivedQuestionPoints(q).maxPoints,
          data: q.data,
          groupClientKey: q.groupClientKey,
          rubricId: q.rubricId ?? null,
          gradingStrategy:
            gradingMode === 'HYBRID'
              ? (q.gradingStrategy ?? 'AUTO')
              : undefined,
          image: imageJson,
        };
      }),
      questionGroups: questionGroups.map((g) => ({
        clientKey: g.clientKey,
        name: g.name.trim() || 'Unnamed Group',
        rubricId: g.rubricId ?? null,
      })),
    };
  }

  // -- Autosave (debounced) --

  const [isReadOnly, setIsReadOnly] = useState(false);

  async function performAutosave() {
    if (!resolvedId || isReadOnly) return;
    setSaveState('saving');
    try {
      const result = await updateAssignmentTemplate(resolvedId, buildPayload(), {
        suppressAuthRedirect: true,
      });
      // Refresh question IDs after save
      const idMap = new Map<number, number>();
      result.questions.forEach((q, idx) => idMap.set(idx, q.id));
      setQuestionIdMap(idMap);
      setSaveState('saved');
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } }).response?.status;
      if (status === 409) {
        // Used or archived templates become read-only in the studio.
        setIsReadOnly(true);
        setSaveState('idle');
        toast.error('This assignment template is archived or has already been used and cannot be modified.');
      } else {
        setSaveState('error');
      }
    }
  }

  // Trigger autosave 3s after any content change (drafts only)
  useEffect(() => {
    if (isLoading || !resolvedId || isReadOnly || !isDraft) return;

    if (!autosavePrimedRef.current) {
      autosavePrimedRef.current = true;
      return;
    }

    if (autosaveTimerRef.current) {
      clearTimeout(autosaveTimerRef.current);
    }
    autosaveTimerRef.current = setTimeout(() => {
      void performAutosave();
    }, 3000);

    return () => {
      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    title,
    category,
    gradingMode,
    scoringPolicy,
    assignmentTemplateRubricId,
    questions,
    questionGroups,
    resolvedId,
    isLoading,
  ]);

  // -- Publish --

  async function handlePublish() {
    if (!resolvedId) return;
    if (!validate()) {
      toast.error('Fix validation issues before publishing.');
      return;
    }

    setIsPublishing(true);
    try {
      // Save latest state first
      await updateAssignmentTemplate(resolvedId, buildPayload(), {
        suppressAuthRedirect: true,
      });
      // Then publish
      await publishAssignmentTemplate(resolvedId);
      toast.success('Assignment template published');
      router.push(`/dashboard/assignment-templates/${resolvedId}`);
    } catch (err: unknown) {
      toast.error(toErrorMessage(err, 'Failed to publish'));
    } finally {
      setIsPublishing(false);
    }
  }

  // -- Delete draft --

  async function handleDeleteDraft() {
    if (!resolvedId || !isDraft) return;
    try {
      await deleteAssignmentTemplate(resolvedId);
      toast.success('Draft deleted');
      router.push('/dashboard/assignment-templates');
    } catch {
      toast.error('Failed to delete draft');
    }
  }

  // -- Submit (non-draft save for published assignment templates) --

  async function handleSubmit(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (isDraft) {
      void handlePublish();
      return;
    }
    if (isReadOnly) {
      toast.error('This assignment template is linked to assignments and cannot be modified.');
      return;
    }
    if (!validate()) {
      toast.error('Please fix the validation issues before saving.');
      return;
    }

    setIsSubmitting(true);
    try {
      await updateAssignmentTemplate(resolvedId!, buildPayload(), {
        suppressAuthRedirect: true,
      });
      toast.success('Assignment template updated');
    } catch (err: unknown) {
      if (getStatusCode(err) === 409) {
        setIsReadOnly(true);
        toast.error(
          'This assignment template is linked to assignments and cannot be modified.',
        );
      } else {
        toast.error(toErrorMessage(err, 'Failed to save assignment template'));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleCancel() {
    if (resolvedId && !isDraft) {
      router.push(`/dashboard/assignment-templates/${resolvedId}`);
    } else {
      router.push('/dashboard/assignment-templates');
    }
  }

  // -- Derived UI state --

  const selectedQuestion = questions[selectedQuestionIndex];
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
      onKeyDownCapture={(event) => {
        if (event.key !== 'Enter') return;
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;
        if (['button', 'submit', 'checkbox', 'radio', 'file'].includes(target.type)) {
          return;
        }
        event.preventDefault();
      }}
      className="flex flex-col h-[calc(100vh-64px)] overflow-hidden -m-8 -mt-8"
    >
      {/* Top header bar */}
      <AssignmentTemplateStudioHeader
        title={title}
        onTitleChange={(t) => {
          clearValidationAttention();
          setTitle(t);
        }}
        titleError={titleError}
        titleHighlightSignal={
          activeValidationIssue?.section === 'title'
            ? validationFocusSignal
            : undefined
        }
        status={assignmentTemplateStatus}
        isDraft={isDraft}
        isReadOnly={isReadOnly}
        saveState={saveState}
        isPublishing={isPublishing}
        isSaving={isSubmitting}
        onPublish={() => void handlePublish()}
        onSave={() => void handleSubmit()}
        onDeleteDraft={() => void handleDeleteDraft()}
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
            'w-[320px] border-r border-border bg-muted/30 flex flex-col shrink-0 overflow-hidden transition-transform duration-200',
            'max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:z-20 max-lg:w-full max-lg:bg-background',
            mobileView === 'structure'
              ? 'max-lg:translate-x-0'
              : 'max-lg:-translate-x-full lg:translate-x-0',
          )}
        >
          <StructureRail
            questions={deferredQuestions}
            questionGroups={deferredQuestionGroups}
            selectedIndex={selectedQuestionIndex}
            onSelectQuestion={(idx) => {
              setSelectedQuestionIndex(idx);
              setAssignGroupKey(questions[idx]?.groupClientKey ?? '__NONE__');
              setMobileView('editor');
            }}
            onBackToEditor={() => setMobileView('editor')}
            onAddQuestion={addQuestion}
            onAddGroup={(name) => addQuestionGroup(name)}
            onRenameGroup={(clientKey, newName) => updateQuestionGroup(clientKey, { name: newName })}
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
            onAssignGroup={(questionIndex, groupClientKey) => {
              const question = questions[questionIndex];
              if (question) {
                clearValidationAttention();
                handleQuestionChange(questionIndex, {
                  ...question,
                  groupClientKey: groupClientKey,
                });
                setAssignGroupKey(groupClientKey ?? '__NONE__');
                setSelectedQuestionIndex(questionIndex);
                setMobileView('editor');
              }
            }}
            groupByKey={groupByKey}
            highlightQuestionListSignal={
              activeValidationIssue?.section === 'questionList'
                ? validationFocusSignal
                : undefined
            }
          />
        </aside>

        {/* Center editor */}
        <main
          className={cn(
            'flex-1 bg-background overflow-y-auto transition-opacity duration-200',
            mobileView !== 'editor' && 'max-lg:hidden',
          )}
        >
          <div className="py-4 px-4 lg:px-6">
            <QuestionStudio
              question={selectedQuestion}
              questionIndex={selectedQuestionIndex}
              selectedEffectiveRubricName={selectedEffectiveRubricName}
              selectedGroupName={selectedGroup?.name ?? null}
              rubricSource={
                selectedQuestion?.rubricId != null
                  ? 'Question'
                  : selectedQuestion?.groupClientKey &&
                      selectedGroup?.rubricId != null
                    ? 'Group'
                    : selectedEffectiveRubricId != null
                      ? 'AssignmentTemplate'
                    : 'N/A'
              }
              activeIssue={
                activeValidationIssue &&
                activeValidationIssue.panel === 'editor'
                  ? {
                      ...activeValidationIssue,
                      id: `${activeValidationIssue.id}:${validationFocusSignal}`,
                    }
                  : null
              }
              questionImage={selectedQuestion?.questionImage ?? null}
              onUploadImage={
                resolvedId && !isReadOnly
                  ? (file) =>
                      handleUploadQuestionImage(selectedQuestionIndex, file)
                  : undefined
              }
              onRemoveImage={
                resolvedId && !isReadOnly
                  ? () =>
                      handleRemoveQuestionImage(selectedQuestionIndex)
                  : undefined
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
            'w-[320px] border-l border-border bg-muted/30 shrink-0 overflow-hidden transition-transform duration-200',
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
            submissionMode={submissionMode}
            onSubmissionModeChange={setSubmissionMode}
            activeQuestion={selectedQuestion}
            onActiveQuestionPointsChange={handleActiveQuestionPointsChange}
            onActiveQuestionGradingStrategyChange={handleActiveQuestionGradingStrategyChange}
            questions={deferredQuestions}
            questionsError={questionsError}
            issues={deferredValidationIssues}
            activeIssue={
              activeValidationIssue && activeValidationIssue.panel === 'settings'
                ? {
                    ...activeValidationIssue,
                    id: `${activeValidationIssue.id}:${validationFocusSignal}`,
                  }
                : null
            }
            onNavigateToIssue={navigateToIssue}
            isRubricEnabled={isRubricEnabled}
            isRubricsLoading={isRubricsLoading}
            rubrics={rubrics}
            assignmentTemplateRubricId={assignmentTemplateRubricId}
            onAssignmentTemplateRubricChange={handleAssignmentTemplateRubricChange}
            activeQuestionRubricId={selectedQuestion?.rubricId ?? null}
            onActiveQuestionRubricChange={handleActiveQuestionRubricChange}
            onOpenQuickRubric={() => setIsQuickRubricOpen(true)}
            onOpenInlineRubricEditor={openInlineRubricEditor}
            onOpenRubricPreview={openRubricPreview}
            questionGroups={deferredQuestionGroups}
            newGroupName={newGroupName}
            onNewGroupNameChange={setNewGroupName}
            onCreateGroup={createGroupFromInput}
            assignGroupKey={assignGroupKey}
            onAssignGroupKeyChange={handleAssignGroupKeyChange}
            selectedAssignGroup={selectedAssignGroup}
            questionCountByGroupKey={questionCountByGroupKey}
            rubricById={rubricById}
            onUpdateQuestionGroup={handleUpdateQuestionGroup}
            onRemoveQuestionGroup={removeQuestionGroup}
            onUngroupActiveQuestion={handleUngroupActiveQuestion}
            category={category}
            categoryOptions={categoryOptions}
            isCategoryComposerOpen={isCategoryComposerOpen}
            onCategoryComposerOpenChange={setIsCategoryComposerOpen}
            categoryDraft={categoryDraft}
            onCategoryDraftChange={setCategoryDraft}
            onApplyCategoryDraft={applyCategoryDraft}
            onCancelCategoryComposer={cancelCategoryComposer}
            onChooseCategoryFromBank={chooseCategoryFromBank}
            onClearCategory={clearCategory}
            onBackToEditor={() => setMobileView('editor')}
          />
        </aside>
      </div>

      {/* Hidden action bar with rubric drawers */}
      <div className="hidden">
        <AssignmentTemplateActionBar
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
