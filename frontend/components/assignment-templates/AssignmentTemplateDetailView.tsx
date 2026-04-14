'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  ChevronDown,
  Eye,
  GripVertical,
  Loader2,
  Pencil,
  Trash2,
} from 'lucide-react';
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
import {
  deleteAssignmentTemplate,
  getAssignmentTemplate,
  updateAssignmentTemplate,
  type AssignmentTemplate,
  type AssignmentTemplateInput,
  type GradingMode,
  type Question,
} from '@/lib/assignment-template-api';
import { listRubrics, type Rubric } from '@/lib/rubric-api';
import RubricTemplatePreviewDrawer from '@/components/assignment-templates/RubricTemplatePreviewDrawer';
import { toErrorMessage } from '@/lib/utils';

function formatPoints(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(2).replace(/\.?0+$/, '');
}

function formatQuestionKind(kind: Question['type']): string {
  switch (kind) {
    case 'MULTIPLE_CHOICE':
      return 'Multiple Choice';
    case 'SHORT_ANSWER':
      return 'Short Answer';
    case 'NUMBER_SCALE':
      return 'Number Scale';
    default:
      return kind;
  }
}

function isManualQuestion(question: Question, gradingMode: GradingMode): boolean {
  if (gradingMode === 'MANUAL') return true;
  if (gradingMode === 'HYBRID') return question.gradingStrategy === 'MANUAL';
  return false;
}

type RubricSource = 'Question' | 'Group' | 'N/A';

function getEffectiveRubricMeta(
  question: Question,
  groupRubricByGroupId: Map<number, number | null>,
  rubricById: Map<number, Rubric>,
): { rubricId: number | null; rubric: Rubric | null; source: RubricSource } {
  const groupRubricId =
    question.groupId != null ? (groupRubricByGroupId.get(question.groupId) ?? null) : null;
  const rubricId = question.rubricId ?? groupRubricId;
  const rubric = rubricId != null ? (rubricById.get(rubricId) ?? null) : null;
  const source: RubricSource =
    question.rubricId != null ? 'Question' : rubricId != null ? 'Group' : 'N/A';
  return { rubricId, rubric, source };
}

type AssignmentTemplateDetailViewProps = {
  assignmentTemplateId: number;
  canManage: boolean;
};

export default function AssignmentTemplateDetailView({
  assignmentTemplateId,
  canManage,
}: AssignmentTemplateDetailViewProps) {
  const router = useRouter();

  const [assignmentTemplate, setAssignmentTemplate] = useState<AssignmentTemplate | null>(null);
  const [rubricById, setRubricById] = useState<Map<number, Rubric>>(new Map());
  const [selectedQuestionId, setSelectedQuestionId] = useState<number | null>(null);
  const [expandedQuestionIds, setExpandedQuestionIds] = useState<Set<number>>(new Set());
  const [isRubricPreviewOpen, setIsRubricPreviewOpen] = useState(false);
  const [previewRubricId, setPreviewRubricId] = useState<number | null>(null);
  const [draggedQuestionId, setDraggedQuestionId] = useState<number | null>(null);
  const [dragOverBucketKey, setDragOverBucketKey] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isReassigningGroup, setIsReassigningGroup] = useState(false);

  const loadAssignmentTemplate = useCallback(async () => {
    setLoadError(null);
    try {
      const [data, rubrics] = await Promise.all([
        getAssignmentTemplate(assignmentTemplateId),
        listRubrics().catch(() => [] as Rubric[]),
      ]);
      setAssignmentTemplate(data);
      setRubricById(new Map(rubrics.map((rubric) => [rubric.id, rubric])));
    } catch {
      setLoadError('Failed to load assignment template.');
    } finally {
      setIsLoading(false);
    }
  }, [assignmentTemplateId]);

  useEffect(() => {
    setIsLoading(true);
    void loadAssignmentTemplate();
  }, [loadAssignmentTemplate]);

  useEffect(() => {
    if (!assignmentTemplate) return;
    const exists =
      selectedQuestionId != null &&
      assignmentTemplate.questions.some((q) => q.questionId === selectedQuestionId);
    if (!exists) {
      setSelectedQuestionId(assignmentTemplate.questions[0]?.questionId ?? null);
    }
  }, [assignmentTemplate, selectedQuestionId]);

  useEffect(() => {
    if (!assignmentTemplate) return;
    const validQuestionIds = new Set(assignmentTemplate.questions.map((q) => q.questionId));
    setExpandedQuestionIds((previous) => {
      const next = new Set(
        [...previous].filter((questionId) => validQuestionIds.has(questionId)),
      );
      if (next.size === 0 && assignmentTemplate.questions[0]) {
        next.add(assignmentTemplate.questions[0].questionId);
      }
      return next;
    });
  }, [assignmentTemplate]);

  async function handleDelete() {
    setIsDeleting(true);
    try {
      await deleteAssignmentTemplate(assignmentTemplateId);
      toast.success('Assignment template deleted.');
      router.push('/dashboard/assignment-templates');
    } catch (error: unknown) {
      const axErr = error as { response?: { data?: { detail?: string }; status?: number } };
      if (
        axErr.response?.data?.detail
          ?.toLowerCase()
          .includes('referenced') ||
        axErr.response?.status === 409
      ) {
        toast.error('Cannot delete — assignment template is referenced by assignments.');
      } else {
        toast.error(toErrorMessage(error, 'Failed to delete assignment template.'));
      }
    } finally {
      setIsDeleting(false);
    }
  }

  function openRubricPreview(rubricId: number | null | undefined) {
    if (rubricId == null) return;
    setPreviewRubricId(rubricId);
    setIsRubricPreviewOpen(true);
  }

  function openFullRubricEditor(rubricId: number) {
    if (canManage) {
      router.push(`/dashboard/rubrics/${rubricId}/edit`);
      return;
    }
    router.push(`/dashboard/rubrics/${rubricId}`);
  }

  function buildAssignmentTemplatePayloadForUpdate(
    current: AssignmentTemplate,
    nextQuestions: Question[],
  ): AssignmentTemplateInput {
    const groupClientKeyById = new Map<number, string>(
      current.questionGroups.map((group) => [group.id, `existing-group-${group.id}`]),
    );

    return {
      title: current.title,
      category: current.category,
      gradingMode: current.gradingMode,
      scoringPolicy: current.scoringPolicy,
      questionGroups: current.questionGroups.map((group) => ({
        clientKey: groupClientKeyById.get(group.id) ?? `existing-group-${group.id}`,
        name: group.name,
        rubricId: group.rubricId,
      })),
      questions: nextQuestions.map((question) => ({
        type: question.type,
        prompt: question.prompt,
        maxPoints: question.maxPoints,
        data: question.data ?? undefined,
        groupClientKey:
          question.groupId != null ? groupClientKeyById.get(question.groupId) : undefined,
        rubricId: question.rubricId,
        gradingStrategy:
          current.gradingMode === 'HYBRID' ? question.gradingStrategy : undefined,
      })),
    };
  }

  async function handleMoveQuestionToGroup(
    questionId: number,
    targetGroupId: number | null,
  ) {
    if (!assignmentTemplate || !canManage || isReassigningGroup) return;

    const target = assignmentTemplate.questions.find((q) => q.questionId === questionId);
    if (!target || target.groupId === targetGroupId) return;

    const previousAssignmentTemplate = assignmentTemplate;
    const nextQuestions = assignmentTemplate.questions.map((question) =>
      question.questionId === questionId ? { ...question, groupId: targetGroupId } : question,
    );
    const optimisticAssignmentTemplate: AssignmentTemplate = {
      ...assignmentTemplate,
      questions: nextQuestions,
    };

    setAssignmentTemplate(optimisticAssignmentTemplate);
    setIsReassigningGroup(true);
    setDragOverBucketKey(null);
    setDraggedQuestionId(null);

    try {
      const payload = buildAssignmentTemplatePayloadForUpdate(assignmentTemplate, nextQuestions);
      const updated = await updateAssignmentTemplate(assignmentTemplate.id, payload);
      setAssignmentTemplate(updated);
      const targetLabel =
        targetGroupId != null
          ? updated.questionGroups.find((group) => group.id === targetGroupId)?.name ??
            'Selected group'
          : 'Ungrouped';
      toast.success(`Question moved to ${targetLabel}.`);
    } catch (error: unknown) {
      setAssignmentTemplate(previousAssignmentTemplate);
      toast.error(toErrorMessage(error, 'Failed to move question between groups.'));
    } finally {
      setIsReassigningGroup(false);
    }
  }

  const groupedQuestionBuckets = useMemo(() => {
    if (!assignmentTemplate)
      return [] as Array<{
        key: string;
        title: string;
        groupId: number | null;
        questions: Question[];
      }>;

    const buckets: Array<{
      key: string;
      title: string;
      groupId: number | null;
      questions: Question[];
    }> = [];
    const byGroupId = new Map<number, Question[]>();
    const ungrouped: Question[] = [];

    for (const question of assignmentTemplate.questions) {
      if (question.groupId != null) {
        const arr = byGroupId.get(question.groupId) ?? [];
        arr.push(question);
        byGroupId.set(question.groupId, arr);
      } else {
        ungrouped.push(question);
      }
    }

    const orderedGroups = [...assignmentTemplate.questionGroups].sort(
      (a, b) => a.orderIndex - b.orderIndex,
    );

    for (const group of orderedGroups) {
      buckets.push({
        key: `group-${group.id}`,
        title: group.name,
        groupId: group.id,
        questions: byGroupId.get(group.id) ?? [],
      });
    }

    buckets.push({
      key: 'ungrouped',
      title: 'Ungrouped',
      groupId: null,
      questions: ungrouped,
    });

    return buckets;
  }, [assignmentTemplate]);

  const questionNumberById = useMemo(() => {
    if (!assignmentTemplate) return new Map<number, number>();
    return new Map(
      assignmentTemplate.questions.map((question, idx) => [question.questionId, idx + 1]),
    );
  }, [assignmentTemplate]);

  const totalPoints = useMemo(() => {
    if (!assignmentTemplate) return 0;
    return assignmentTemplate.questions.reduce((sum, question) => sum + question.maxPoints, 0);
  }, [assignmentTemplate]);

  const toggleQuestionExpanded = useCallback((questionId: number) => {
    setExpandedQuestionIds((previous) => {
      const next = new Set(previous);
      if (next.has(questionId)) {
        next.delete(questionId);
      } else {
        next.add(questionId);
      }
      return next;
    });
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="space-y-6 p-6">
        <Link
          href="/dashboard/assignment-templates"
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to assignment templates
        </Link>
        <p className="text-sm text-destructive">{loadError}</p>
      </div>
    );
  }

  if (!assignmentTemplate) {
    return (
      <div className="space-y-6 p-6">
        <Link
          href="/dashboard/assignment-templates"
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to assignment templates
        </Link>
        <p className="text-sm text-muted-foreground">Assignment template not found.</p>
      </div>
    );
  }

  const groupRubricByGroupId = new Map<number, number | null>(
    assignmentTemplate.questionGroups.map((group) => [group.id, group.rubricId]),
  );

  const selectedQuestion =
    selectedQuestionId != null
      ? assignmentTemplate.questions.find((q) => q.questionId === selectedQuestionId) ?? null
      : null;
  const selectedQuestionIndex =
    selectedQuestionId != null
      ? assignmentTemplate.questions.findIndex((q) => q.questionId === selectedQuestionId)
      : -1;
  const selectedRubricMeta = selectedQuestion
    ? getEffectiveRubricMeta(selectedQuestion, groupRubricByGroupId, rubricById)
    : null;
  const selectedGroupName =
    selectedQuestion?.groupId != null
      ? assignmentTemplate.questionGroups.find((group) => group.id === selectedQuestion.groupId)?.name ??
        'Unknown Group'
      : 'Ungrouped';

  return (
    <div className="space-y-6 px-6 py-6 w-full">
      <Link
        href="/dashboard/assignment-templates"
        className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to assignment templates
      </Link>

      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          {assignmentTemplate.title}
        </h1>
        {assignmentTemplate.category && (
          <span className="bg-muted text-muted-foreground px-2 py-0.5 rounded text-xs font-medium">
            {assignmentTemplate.category}
          </span>
        )}
        <span className="bg-muted text-muted-foreground px-2 py-0.5 rounded text-xs font-medium">
          {assignmentTemplate.gradingMode}
        </span>
        <span className="bg-muted text-muted-foreground px-2 py-0.5 rounded text-xs font-medium">
          {assignmentTemplate.scoringPolicy === 'COMPLETION'
            ? 'Scoring: Completion (100)'
            : 'Scoring: Standard'}
        </span>
        <span className="bg-muted text-muted-foreground px-2 py-0.5 rounded text-xs font-medium">
          Total: {formatPoints(totalPoints)} pts
        </span>

        {canManage && (
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => router.push(`/dashboard/assignment-templates/${assignmentTemplateId}/edit`)}
            >
              <Pencil className="h-4 w-4" />
              <span className="sr-only">Edit</span>
            </Button>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                  <span className="sr-only">Delete</span>
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete Assignment Template</AlertDialogTitle>
                  <AlertDialogDescription>
                    Are you sure you want to delete this assignment template? This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    variant="destructive"
                    disabled={isDeleting}
                    onClick={(event) => {
                      event.preventDefault();
                      void handleDelete();
                    }}
                  >
                    {isDeleting ? 'Deleting...' : 'Delete'}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <section className="space-y-4 min-w-0">
          {assignmentTemplate.questions.length === 0 &&
            assignmentTemplate.questionGroups.length === 0 && (
            <p className="text-sm text-muted-foreground">No questions in this assignment template.</p>
          )}

          {groupedQuestionBuckets.map((bucket) => (
            <div
              key={bucket.key}
              className={`rounded-sm border bg-card p-4 transition-colors ${
                dragOverBucketKey === bucket.key
                  ? 'border-primary bg-accent/20'
                  : 'border-border'
              }`}
              onDragOver={(event) => {
                if (!canManage || draggedQuestionId == null || isReassigningGroup) return;
                event.preventDefault();
                setDragOverBucketKey(bucket.key);
              }}
              onDragLeave={() => {
                if (dragOverBucketKey === bucket.key) {
                  setDragOverBucketKey(null);
                }
              }}
              onDrop={(event) => {
                if (!canManage || draggedQuestionId == null || isReassigningGroup) return;
                event.preventDefault();
                void handleMoveQuestionToGroup(draggedQuestionId, bucket.groupId);
              }}
            >
              <div className="mb-3 flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground">
                  {bucket.title}
                </h2>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    {bucket.questions.length} question(s)
                  </span>
                  {canManage && (
                    <span className="text-[11px] text-muted-foreground">
                      Drag questions here
                    </span>
                  )}
                </div>
              </div>

              {bucket.questions.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  {canManage
                    ? 'No questions in this group. Drop a question here.'
                    : 'No questions in this group.'}
                </p>
              ) : (
                <div className="space-y-2">
                  {bucket.questions.map((question) => (
                    <QuestionCard
                      key={question.questionId}
                      question={question}
                      index={questionNumberById.get(question.questionId) ?? 1}
                      gradingMode={assignmentTemplate.gradingMode}
                      isSelected={selectedQuestionId === question.questionId}
                      isExpanded={expandedQuestionIds.has(question.questionId)}
                      rubricById={rubricById}
                      groupRubricByGroupId={groupRubricByGroupId}
                      onSelect={() => setSelectedQuestionId(question.questionId)}
                      onToggleExpanded={() => toggleQuestionExpanded(question.questionId)}
                      canDrag={canManage && !isReassigningGroup}
                      onDragStart={() => {
                        setDraggedQuestionId(question.questionId);
                        setSelectedQuestionId(question.questionId);
                      }}
                      onDragEnd={() => {
                        setDraggedQuestionId(null);
                        setDragOverBucketKey(null);
                      }}
                      onPreviewRubric={openRubricPreview}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </section>

        <aside className="space-y-4 xl:sticky xl:top-4">
          <div className="rounded-sm border border-border bg-card p-4 space-y-2">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Template Inspector</p>
            {selectedQuestion ? (
              <>
                <h2 className="text-base font-semibold text-foreground">
                  Question {selectedQuestionIndex + 1}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {formatQuestionKind(selectedQuestion.type)} • {selectedQuestion.maxPoints} pts
                </p>
                <p className="text-xs text-muted-foreground">
                  Group: {selectedGroupName} • Grading: {selectedQuestion.gradingStrategy}
                </p>
                <p className="text-xs text-muted-foreground">
                  Rubric source: {selectedRubricMeta?.source ?? 'N/A'}
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Select a question to inspect.</p>
            )}
          </div>

          <div className="rounded-sm border border-border bg-card p-4 space-y-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Rubric Preview</p>
            {selectedQuestion && selectedRubricMeta?.rubricId != null ? (
              <div className="rounded-sm border border-border bg-muted/20 p-3 space-y-2">
                <p className="text-sm text-foreground font-medium">
                  {selectedRubricMeta.rubric?.title ?? 'Unavailable'}
                </p>
                <p className="text-xs text-muted-foreground">
                  Open the drawer to view the full rubric grid and levels.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => openRubricPreview(selectedRubricMeta.rubricId)}
                >
                  <Eye className="mr-1 h-4 w-4" />
                  Preview In Drawer
                </Button>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Selected question has no rubric attached.
              </p>
            )}
          </div>
        </aside>
      </div>

      <RubricTemplatePreviewDrawer
        open={isRubricPreviewOpen}
        onOpenChange={setIsRubricPreviewOpen}
        rubricId={previewRubricId}
        onOpenFullEditor={openFullRubricEditor}
      />
    </div>
  );
}

function QuestionCard({
  question,
  index,
  gradingMode,
  isSelected,
  isExpanded,
  rubricById,
  groupRubricByGroupId,
  onSelect,
  onToggleExpanded,
  canDrag,
  onDragStart,
  onDragEnd,
  onPreviewRubric,
}: {
  question: Question;
  index: number;
  gradingMode: GradingMode;
  isSelected: boolean;
  isExpanded: boolean;
  rubricById: Map<number, Rubric>;
  groupRubricByGroupId: Map<number, number | null>;
  onSelect: () => void;
  onToggleExpanded: () => void;
  canDrag: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onPreviewRubric: (rubricId: number | null | undefined) => void;
}) {
  const rowRef = useRef<HTMLDivElement | null>(null);
  const rubricMeta = getEffectiveRubricMeta(question, groupRubricByGroupId, rubricById);
  const canPreviewRubric = isManualQuestion(question, gradingMode) && rubricMeta.rubricId != null;
  const rubricLabel =
    rubricMeta.rubric != null
      ? `Rubric: ${rubricMeta.rubric.title}`
      : rubricMeta.rubricId != null
        ? 'Rubric: Unavailable'
        : 'Rubric: None';

  return (
    <div
      ref={rowRef}
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onSelect();
        }
      }}
      className={`relative w-full rounded-sm border bg-card text-left transition-colors ${
        isSelected ? 'border-primary ring-1 ring-primary/30' : 'border-border hover:bg-muted/20'
      }`}
      aria-pressed={isSelected}
    >
      {canDrag && (
        <span
          role="button"
          tabIndex={0}
          draggable
          aria-label={`Drag question ${index}`}
          className="absolute inset-y-0 left-0 inline-flex w-8 cursor-grab items-center justify-center rounded-l-sm border-r border-border bg-muted/30 text-muted-foreground hover:text-foreground active:cursor-grabbing"
          onClick={(event) => event.stopPropagation()}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              event.stopPropagation();
            }
          }}
          onDragStart={(event) => {
            event.stopPropagation();
            if (rowRef.current) {
              event.dataTransfer.setDragImage(rowRef.current, 24, 18);
            }
            event.dataTransfer.effectAllowed = 'move';
            onDragStart();
          }}
          onDragEnd={(event) => {
            event.stopPropagation();
            onDragEnd();
          }}
        >
          <GripVertical className="h-4 w-4" />
        </span>
      )}

      <div className={`flex items-start justify-between gap-3 py-2.5 pr-3 ${canDrag ? 'pl-11' : 'pl-3'}`}>
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-sm font-semibold text-foreground">Q{index}</p>
          <p
            className="truncate text-sm text-foreground"
            title={question.prompt.trim() || 'Untitled question'}
          >
            {question.prompt.trim() || 'Untitled question'}
          </p>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
            <span>{formatQuestionKind(question.type)}</span>
            <span>•</span>
            <span>{question.maxPoints} pts</span>
            <span>•</span>
            <span>Grading: {question.gradingStrategy}</span>
            <span>•</span>
            <span>{rubricLabel}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {canPreviewRubric && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8"
              onClick={(event) => {
                event.stopPropagation();
                onPreviewRubric(rubricMeta.rubricId);
              }}
            >
              <Eye className="mr-1 h-4 w-4" />
              Preview Rubric
            </Button>
          )}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            aria-label={isExpanded ? `Collapse question ${index}` : `Expand question ${index}`}
            onClick={(event) => {
              event.stopPropagation();
              onToggleExpanded();
            }}
          >
            <ChevronDown
              className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            />
          </Button>
        </div>
      </div>

      {isExpanded && (
        <div className={`border-t border-border bg-muted/10 py-3 pr-3 space-y-2 ${canDrag ? 'pl-11' : 'pl-3'}`}>
          <p className="text-sm text-foreground">{question.prompt}</p>
          <p className="text-xs text-muted-foreground">Rubric source: {rubricMeta.source}</p>
          <QuestionDetails question={question} />
        </div>
      )}
    </div>
  );
}

function QuestionDetails({ question }: { question: Question }) {
  const data = question.data;

  switch (question.type) {
    case 'MULTIPLE_CHOICE':
      return <MultipleChoiceDetails data={data} />;
    case 'SHORT_ANSWER':
      return <ShortAnswerDetails data={data} />;
    case 'NUMBER_SCALE':
      return <NumberScaleDetails question={question} />;
    default:
      return null;
  }
}

function MultipleChoiceDetails({
  data,
}: {
  data: Question['data'];
}) {
  if (!data?.choices || data.choices.length === 0) {
    return <p className="text-sm text-muted-foreground">No choices defined.</p>;
  }

  return (
    <div className="space-y-1">
      {data.selectAll && (
        <p className="text-xs text-muted-foreground italic">(Select all that apply)</p>
      )}
      <ol className="list-decimal list-inside space-y-1">
        {data.choices.map((choice, i) => (
          <li key={i} className="text-sm text-foreground">
            &quot;{choice.prompt}&quot;{' '}
            <span className="text-muted-foreground">&mdash; {choice.score} pts</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function ShortAnswerDetails({ data }: { data: Question['data'] }) {
  return (
    <div className="space-y-1 text-sm text-muted-foreground">
      <p>Case Sensitive: {data?.caseSensitive ? 'Yes' : 'No'}</p>
      <p>Trim Whitespace: {data?.trim ? 'Yes' : 'No'}</p>
    </div>
  );
}

function NumberScaleDetails({ question }: { question: Question }) {
  const min = question.data?.min ?? question.min;
  const max = question.data?.max ?? question.max;
  const target = question.data?.target;

  return (
    <div className="space-y-1 text-sm text-muted-foreground">
      <p>
        Range: {min ?? '?'} &ndash; {max ?? '?'}
      </p>
      {target !== undefined && target !== null && <p>Target: {target}</p>}
    </div>
  );
}
