'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  Check,
  ChevronDown,
  ChevronRight,
  FileText,
  Lock,
  Pencil,
  Plus,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react';
import { toast } from 'sonner';

import QuestionTypeConfig from '@/components/assignment-templates/studio/QuestionTypeConfig';
import ImagePicker from '@/components/media/ImagePicker';
import RubricGridPreview from '@/components/rubrics/RubricGridPreview';
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
import { Textarea } from '@/components/ui/textarea';
import {
  addAssignmentQuestion,
  addAssignmentTeacherCriterion,
  addAssignmentTeacherCriterionLevel,
  deleteAssignmentQuestion,
  deleteAssignmentQuestionImage,
  deleteAssignmentTeacherCriterion,
  deleteAssignmentTeacherCriterionLevel,
  listReusableAssignmentImages,
  reorderAssignmentQuestions,
  reorderAssignmentTeacherCriteria,
  reorderAssignmentTeacherCriterionLevels,
  reuseAssignmentQuestionImage,
  updateAssignmentQuestion,
  updateAssignmentTeacherCriterion,
  updateAssignmentTeacherCriterionLevel,
  uploadAssignmentQuestionImage,
  type AssignmentContent,
  type AssignmentQuestion,
  type AssignmentTeacherCriterion,
} from '@/lib/assignment-api';
import type { QuestionData, QuestionKind } from '@/lib/assignment-template-api';
import { getRubric, type Rubric } from '@/lib/rubric-api';
import { cn, toErrorMessage } from '@/lib/utils';

type Props = {
  assignmentId: number;
  content: AssignmentContent;
  canCompose: boolean;
  onContentChange: (next: AssignmentContent) => void;
};

type QuestionDraft = {
  type: QuestionKind;
  prompt: string;
  maxPoints: string;
  data: QuestionData;
};

type CriterionDraft = {
  title: string;
  description: string;
  weight: string;
};

type CriterionLevelDraft = {
  label: string;
  description: string;
  points: string;
};

type SelectedQuestionState = number | 'new' | null;

const EMPTY_CRITERION: CriterionDraft = {
  title: '',
  description: '',
  weight: '1',
};

const EMPTY_LEVEL: CriterionLevelDraft = {
  label: '',
  description: '',
  points: '1',
};

function moveItem<T>(items: T[], from: number, to: number): T[] {
  if (from === to || to < 0 || to >= items.length) return items;
  const next = [...items];
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved);
  return next;
}

function formatPoints(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(2).replace(/\.?0+$/, '');
}

function buildQuestionData(kind: QuestionKind): QuestionData | undefined {
  if (kind === 'MULTIPLE_CHOICE') {
    return {
      choices: [
        { prompt: 'Option 1', score: 0 },
        { prompt: 'Option 2', score: 1 },
      ],
      selectAll: false,
    };
  }
  if (kind === 'NUMBER_SCALE') {
    return { min: 1, max: 5, target: null };
  }
  if (kind === 'SHORT_ANSWER') {
    return { trim: true, caseSensitive: false };
  }
  return {};
}

function makeEmptyQuestionDraft(kind: QuestionKind = 'SHORT_ANSWER'): QuestionDraft {
  return {
    type: kind,
    prompt: '',
    maxPoints: '1',
    data: buildQuestionData(kind) ?? {},
  };
}

function toQuestionDraft(question: AssignmentQuestion): QuestionDraft {
  return {
    type: question.type,
    prompt: question.prompt,
    maxPoints: String(question.maxPoints),
    data: question.data ?? buildQuestionData(question.type) ?? {},
  };
}

function confirmDestructiveAction(message: string): boolean {
  if (typeof window === 'undefined' || typeof window.confirm !== 'function') {
    return true;
  }
  return window.confirm(message);
}

function formatQuestionKind(kind: QuestionKind): string {
  switch (kind) {
    case 'MULTIPLE_CHOICE':
      return 'Multiple choice';
    case 'SHORT_ANSWER':
      return 'Short answer';
    case 'NUMBER_SCALE':
      return 'Number scale';
    case 'MOOD_METER':
      return 'Mood meter';
    case 'FILE_UPLOAD':
      return 'File upload';
    default:
      return kind;
  }
}

function describeQuestionData(question: AssignmentQuestion): JSX.Element | null {
  const data = question.data ?? {};

  if (question.type === 'MULTIPLE_CHOICE') {
    const choices = data.choices ?? [];
    return (
      <div className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Answer options
        </p>
        <div className="space-y-2">
          {choices.map((choice, index) => (
            <div
              key={`${question.id}-choice-${index}`}
              className="flex items-center justify-between rounded-xl border border-border/60 bg-card px-3 py-2"
            >
              <span className="text-sm text-foreground">
                {choice.prompt || `Choice ${index + 1}`}
              </span>
              <span className="text-xs text-muted-foreground">
                {formatPoints(choice.score ?? 0)} pts
              </span>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          {data.selectAll
            ? 'Students can select multiple options.'
            : 'Students select one option.'}
        </p>
      </div>
    );
  }

  if (question.type === 'NUMBER_SCALE') {
    return (
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-border/60 bg-card px-3 py-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Min</p>
          <p className="mt-1 text-sm font-medium text-foreground">{data.min ?? 1}</p>
        </div>
        <div className="rounded-xl border border-border/60 bg-card px-3 py-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Max</p>
          <p className="mt-1 text-sm font-medium text-foreground">{data.max ?? 5}</p>
        </div>
        <div className="rounded-xl border border-border/60 bg-card px-3 py-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Target</p>
          <p className="mt-1 text-sm font-medium text-foreground">
            {data.target == null ? 'No exact target' : data.target}
          </p>
        </div>
      </div>
    );
  }

  if (question.type === 'SHORT_ANSWER') {
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-border/60 bg-card px-3 py-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Whitespace</p>
          <p className="mt-1 text-sm font-medium text-foreground">
            {data.trim === false ? 'Preserved' : 'Trimmed'}
          </p>
        </div>
        <div className="rounded-xl border border-border/60 bg-card px-3 py-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Case sensitivity</p>
          <p className="mt-1 text-sm font-medium text-foreground">
            {data.caseSensitive ? 'Sensitive' : 'Insensitive'}
          </p>
        </div>
      </div>
    );
  }

  if (question.type === 'MOOD_METER') {
    return (
      <div className="rounded-xl border border-border/60 bg-card px-3 py-3">
        <p className="text-sm text-muted-foreground">
          Students respond on the Yale RULER Mood Meter. The response grid stays fixed and cannot
          be reconfigured here.
        </p>
      </div>
    );
  }

  return null;
}

function QuestionRail({
  questions,
  selectedQuestion,
  canCompose,
  onSelectQuestion,
  onStartNewQuestion,
  onBackToEditor,
}: {
  questions: AssignmentQuestion[];
  selectedQuestion: SelectedQuestionState;
  canCompose: boolean;
  onSelectQuestion: (questionId: number) => void;
  onStartNewQuestion: () => void;
  onBackToEditor?: () => void;
}) {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-border px-4 py-4">
        <div className="mb-3 flex items-center justify-between lg:hidden">
          <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
            Structure
          </span>
          {onBackToEditor ? (
            <Button type="button" variant="ghost" size="sm" onClick={onBackToEditor}>
              Back
            </Button>
          ) : null}
        </div>
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Structure
            </p>
            <h2 className="mt-2 text-lg font-semibold text-foreground">Question structure</h2>
          </div>
          <span className="rounded-full border border-border/70 bg-muted/40 px-3 py-1 text-xs font-medium text-muted-foreground">
            {questions.length} total
          </span>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          Questions from the shared template stay locked. Add your own questions below without
          changing the original template.
        </p>
        <Button
          type="button"
          className="mt-4 w-full gap-2"
          onClick={onStartNewQuestion}
          disabled={!canCompose}
        >
          <Plus className="h-4 w-4" />
          Add local question
        </Button>
      </div>

      <div className="space-y-2 p-3">
        {questions.map((question, index) => {
          const isSelected = selectedQuestion === question.id;
          const isLocked = question.lockedFromSource;
          return (
            <button
              key={question.id}
              type="button"
              onClick={() => onSelectQuestion(question.id)}
              className={cn(
                'w-full rounded-2xl border px-3 py-3 text-left transition-colors',
                isSelected
                  ? 'border-primary/50 bg-primary/5 shadow-sm'
                  : 'border-border/70 bg-background hover:bg-muted/40',
                isLocked && 'bg-muted/45',
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                      Q{index + 1}
                    </span>
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-medium uppercase tracking-wide',
                        isLocked
                          ? 'bg-muted text-muted-foreground'
                          : 'bg-primary/10 text-primary',
                      )}
                    >
                      {isLocked ? <Lock className="h-3 w-3" /> : <Sparkles className="h-3 w-3" />}
                      {isLocked ? 'Locked' : 'Local'}
                    </span>
                  </div>
                  <p
                    className={cn(
                      'line-clamp-2 text-sm font-medium',
                      isLocked ? 'text-muted-foreground' : 'text-foreground',
                    )}
                  >
                    {question.prompt}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    {formatQuestionKind(question.type)}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatPoints(question.maxPoints)} pts
                  </p>
                </div>
              </div>
            </button>
          );
        })}

        <button
          type="button"
          onClick={onStartNewQuestion}
          disabled={!canCompose}
          className={cn(
            'w-full rounded-2xl border border-dashed px-3 py-4 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60',
            selectedQuestion === 'new'
              ? 'border-primary/50 bg-primary/5'
              : 'border-border/70 bg-background hover:bg-muted/40',
          )}
        >
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-primary/10 p-2 text-primary">
              <Plus className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">New local question</p>
              <p className="text-xs text-muted-foreground">
                Add a teacher-only question after the locked researcher sequence.
              </p>
            </div>
          </div>
        </button>
      </div>
    </div>
  );
}

function LockedQuestionStudio({ question }: { question: AssignmentQuestion }) {
  return (
    <section className="rounded-3xl border border-border bg-card shadow-sm">
      <div className="border-b border-border px-5 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Shared template
            </p>
            <h2 className="mt-2 text-xl font-semibold text-foreground">Locked template question</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              This question was provided by the shared template. You can review it here, but its
              wording, response setup, points, and order stay fixed.
            </p>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-muted px-3 py-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            <Lock className="h-3 w-3" />
            Locked
          </span>
        </div>
      </div>

      <div className="space-y-6 px-5 py-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-border/70 bg-muted/35 px-4 py-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Type</p>
            <p className="mt-1 text-sm font-medium text-foreground">{formatQuestionKind(question.type)}</p>
          </div>
          <div className="rounded-2xl border border-border/70 bg-muted/35 px-4 py-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Points</p>
            <p className="mt-1 text-sm font-medium text-foreground">{formatPoints(question.maxPoints)}</p>
          </div>
          <div className="rounded-2xl border border-border/70 bg-muted/35 px-4 py-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Origin</p>
            <p className="mt-1 text-sm font-medium text-foreground">Shared template</p>
          </div>
        </div>

        <div className="space-y-3">
          <Label className="text-xs font-bold uppercase tracking-[0.18em] text-muted-foreground">
            Prompt
          </Label>
          <div className="rounded-2xl border border-border/70 bg-muted/35 px-4 py-4">
            <p className="text-base leading-relaxed text-foreground">{question.prompt}</p>
          </div>
        </div>

        {question.image && (
          <div className="space-y-3">
            <Label className="text-xs font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Attached image
            </Label>
            <div className="overflow-hidden rounded-2xl border border-border/60">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={question.image.url}
                alt={question.image.originalFilename}
                className="h-60 w-full object-cover"
              />
            </div>
          </div>
        )}

        <div className="space-y-3">
          <Label className="text-xs font-bold uppercase tracking-[0.18em] text-muted-foreground">
            Response configuration
          </Label>
          {describeQuestionData(question)}
        </div>
      </div>
    </section>
  );
}

function InheritedRubricList({ rubric }: { rubric: Rubric }) {
  return (
    <div className="space-y-3">
      <div>
        <p className="text-sm font-semibold text-foreground">{rubric.title}</p>
        {rubric.description ? (
          <p className="mt-1 text-sm text-muted-foreground">{rubric.description}</p>
        ) : null}
      </div>

      {rubric.criteria.length === 0 ? (
        <p className="text-sm text-muted-foreground">No locked rubric criteria were provided.</p>
      ) : (
        <div className="space-y-3">
          {rubric.criteria.map((criterion) => (
            <div
              key={criterion.id}
              className="rounded-2xl border border-border/60 bg-card px-4 py-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-foreground">{criterion.title}</p>
                  {criterion.description ? (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {criterion.description}
                    </p>
                  ) : null}
                </div>
                <span className="rounded-full bg-muted px-2 py-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  {formatPoints(criterion.weight)} wt
                </span>
              </div>
              {criterion.levels.length > 0 ? (
                <div className="mt-3 space-y-2">
                  {criterion.levels.map((level) => (
                    <div
                      key={level.id}
                      className="rounded-xl border border-border/50 bg-background px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium text-foreground">{level.label}</p>
                        <span className="text-xs text-muted-foreground">
                          {formatPoints(level.points)} pts
                        </span>
                      </div>
                      {level.description ? (
                        <p className="mt-1 text-xs text-muted-foreground">{level.description}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TeacherQuestionStudio({
  assignmentId,
  question,
  draft,
  canCompose,
  canMoveUp,
  canMoveDown,
  activeImage,
  isSaving,
  isDeleting,
  onDraftChange,
  onMoveUp,
  onMoveDown,
  onSave,
  onDelete,
  onImageChange,
}: {
  assignmentId: number;
  question: AssignmentQuestion;
  draft: QuestionDraft;
  canCompose: boolean;
  canMoveUp: boolean;
  canMoveDown: boolean;
  activeImage: AssignmentQuestion['image'];
  isSaving: boolean;
  isDeleting: boolean;
  onDraftChange: (next: QuestionDraft) => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onSave: () => void;
  onDelete: () => void;
  onImageChange: (next: AssignmentQuestion['image']) => void;
}) {
  return (
    <section className="rounded-3xl border border-border bg-card shadow-sm">
      <div className="border-b border-border px-5 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Local addition
            </p>
            <h2 className="mt-2 text-xl font-semibold text-foreground">Editable question</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              This question belongs only to this assignment. You can change its prompt, response
              settings, image, and order without affecting the shared template.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-1 text-[11px] font-medium uppercase tracking-wide text-primary">
              <Sparkles className="h-3 w-3" />
              Local
            </span>
            <Button
              type="button"
              size="icon"
              variant="outline"
              className="h-9 w-9"
              disabled={!canCompose || isSaving || isDeleting || !canMoveUp}
              onClick={onMoveUp}
              aria-label={`Move ${question.prompt} earlier`}
            >
              <ArrowUp className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              size="icon"
              variant="outline"
              className="h-9 w-9"
              disabled={!canCompose || isSaving || isDeleting || !canMoveDown}
              onClick={onMoveDown}
              aria-label={`Move ${question.prompt} later`}
            >
              <ArrowDown className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              size="icon"
              variant="outline"
              className="h-9 w-9 text-destructive hover:text-destructive"
              disabled={!canCompose || isSaving || isDeleting}
              onClick={onDelete}
              aria-label={`Remove ${question.prompt}`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <div className="space-y-6 px-5 py-5">
        <div className="grid gap-4 lg:grid-cols-[180px_minmax(0,1fr)_140px]">
          <div className="space-y-2">
            <Label htmlFor={`edit-question-type-${question.id}`}>Type</Label>
            <Select
              value={draft.type}
              onValueChange={(value) =>
                onDraftChange({
                  ...draft,
                  type: value as QuestionKind,
                  data: buildQuestionData(value as QuestionKind) ?? {},
                })
              }
              disabled={!canCompose || isSaving}
            >
              <SelectTrigger id={`edit-question-type-${question.id}`}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="SHORT_ANSWER">Short answer</SelectItem>
                <SelectItem value="MULTIPLE_CHOICE">Multiple choice</SelectItem>
                <SelectItem value="NUMBER_SCALE">Number scale</SelectItem>
                <SelectItem value="MOOD_METER">Mood meter</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor={`edit-question-prompt-${question.id}`}>Prompt</Label>
            <Textarea
              id={`edit-question-prompt-${question.id}`}
              value={draft.prompt}
              onChange={(event) => onDraftChange({ ...draft, prompt: event.target.value })}
              disabled={!canCompose || isSaving}
              rows={4}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={`edit-question-points-${question.id}`}>Points</Label>
            <Input
              id={`edit-question-points-${question.id}`}
              type="number"
              min="0"
              step="0.5"
              value={draft.maxPoints}
              onChange={(event) => onDraftChange({ ...draft, maxPoints: event.target.value })}
              disabled={!canCompose || isSaving}
            />
          </div>
        </div>

        <div className="space-y-3">
          <Label className="text-xs font-bold uppercase tracking-[0.18em] text-muted-foreground">
            Response configuration
          </Label>
          <div className="rounded-2xl border border-border/70 bg-background px-4 py-4">
            <QuestionTypeConfig
              type={draft.type}
              data={draft.data}
              onChange={(nextData) => onDraftChange({ ...draft, data: nextData })}
            />
          </div>
        </div>

        <div className="space-y-3">
          <Label className="text-xs font-bold uppercase tracking-[0.18em] text-muted-foreground">
            Question image
          </Label>
          <div className="rounded-2xl border border-border/70 bg-background px-4 py-4">
            <ImagePicker
              image={activeImage}
              disabled={!canCompose || isSaving || isDeleting}
              emptyLabel="Attach a supporting image"
              emptyHint="Reuse an earlier image or upload a new one for this assignment-only question."
              browseLabel="Reuse Existing Image"
              browseDialogTitle="Choose a reusable question image"
              onBrowse={() => listReusableAssignmentImages(assignmentId)}
              onUpload={async (file) => {
                const next = await uploadAssignmentQuestionImage(assignmentId, question.id, file);
                onImageChange(next);
                toast.success('Question image uploaded.');
                return next;
              }}
              onSelect={async (picked) => {
                const next = await reuseAssignmentQuestionImage(assignmentId, question.id, picked.id);
                onImageChange(next);
                toast.success('Question image attached.');
              }}
              onRemove={async () => {
                await deleteAssignmentQuestionImage(assignmentId, question.id);
                onImageChange(null);
                toast.success('Question image removed.');
              }}
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button type="button" onClick={onSave} disabled={!canCompose || isSaving}>
            <Check className="mr-2 h-4 w-4" />
            Save question
          </Button>
        </div>
      </div>
    </section>
  );
}

function NewQuestionStudio({
  draft,
  canCompose,
  onDraftChange,
  onCreate,
}: {
  draft: QuestionDraft;
  canCompose: boolean;
  onDraftChange: (next: QuestionDraft) => void;
  onCreate: () => void;
}) {
  return (
    <section className="rounded-3xl border border-border bg-card shadow-sm">
      <div className="border-b border-border px-5 py-5">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Local addition
        </p>
        <h2 className="mt-2 text-xl font-semibold text-foreground">New local question</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Add a question that only exists on this assignment. It will appear after the locked
          template questions and can be edited or reordered later.
        </p>
      </div>

      <div className="space-y-6 px-5 py-5">
        <div className="grid gap-4 lg:grid-cols-[180px_minmax(0,1fr)_140px]">
          <div className="space-y-2">
            <Label htmlFor="assignment-question-type">Type</Label>
            <Select
              value={draft.type}
              onValueChange={(value) =>
                onDraftChange({
                  ...draft,
                  type: value as QuestionKind,
                  data: buildQuestionData(value as QuestionKind) ?? {},
                })
              }
              disabled={!canCompose}
            >
              <SelectTrigger id="assignment-question-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="SHORT_ANSWER">Short answer</SelectItem>
                <SelectItem value="MULTIPLE_CHOICE">Multiple choice</SelectItem>
                <SelectItem value="NUMBER_SCALE">Number scale</SelectItem>
                <SelectItem value="MOOD_METER">Mood meter</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="assignment-question-prompt">Prompt</Label>
            <Textarea
              id="assignment-question-prompt"
              value={draft.prompt}
              onChange={(event) => onDraftChange({ ...draft, prompt: event.target.value })}
              disabled={!canCompose}
              rows={4}
              placeholder="Add an assignment-only question"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="assignment-question-points">Points</Label>
            <Input
              id="assignment-question-points"
              type="number"
              min="0"
              step="0.5"
              value={draft.maxPoints}
              onChange={(event) => onDraftChange({ ...draft, maxPoints: event.target.value })}
              disabled={!canCompose}
            />
          </div>
        </div>

        <div className="space-y-3">
          <Label className="text-xs font-bold uppercase tracking-[0.18em] text-muted-foreground">
            Response configuration
          </Label>
          <div className="rounded-2xl border border-border/70 bg-background px-4 py-4">
            <QuestionTypeConfig
              type={draft.type}
              data={draft.data}
              onChange={(nextData) => onDraftChange({ ...draft, data: nextData })}
            />
          </div>
        </div>

        <div className="rounded-2xl border border-dashed border-border/70 bg-background px-4 py-4">
          <p className="text-sm text-muted-foreground">
            You can attach or reuse an image after the question is created. That keeps the media
            library tied to a saved assignment question instead of a temporary draft.
          </p>
        </div>

        <div className="flex justify-end">
          <Button type="button" onClick={onCreate} disabled={!canCompose}>
            <Plus className="mr-2 h-4 w-4" />
            Add question
          </Button>
        </div>
      </div>
    </section>
  );
}

function TeacherCriterionCard({
  assignmentId,
  criterion,
  canCompose,
  canMoveUp,
  canMoveDown,
  onMoveUp,
  onMoveDown,
  onContentChange,
}: {
  assignmentId: number;
  criterion: AssignmentTeacherCriterion;
  canCompose: boolean;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onContentChange: (next: AssignmentContent) => void;
}) {
  const [draft, setDraft] = useState<CriterionLevelDraft>(EMPTY_LEVEL);
  const [criterionDraft, setCriterionDraft] = useState<CriterionDraft>({
    title: criterion.title,
    description: criterion.description,
    weight: String(criterion.weight),
  });
  const [editingLevelId, setEditingLevelId] = useState<number | null>(null);
  const [editingLevelDraft, setEditingLevelDraft] = useState<CriterionLevelDraft>(EMPTY_LEVEL);
  const [isEditingCriterion, setIsEditingCriterion] = useState(false);
  const [isSavingLevel, setIsSavingLevel] = useState(false);
  const [isSavingCriterion, setIsSavingCriterion] = useState(false);
  const [isMovingLevels, setIsMovingLevels] = useState(false);
  const [isDeletingCriterion, setIsDeletingCriterion] = useState(false);
  const [deletingLevelId, setDeletingLevelId] = useState<number | null>(null);

  useEffect(() => {
    setCriterionDraft({
      title: criterion.title,
      description: criterion.description,
      weight: String(criterion.weight),
    });
  }, [criterion]);

  async function handleAddLevel() {
    const label = draft.label.trim();
    const points = Number(draft.points);
    if (!label) {
      toast.error('Level label is required.');
      return;
    }
    if (!Number.isFinite(points) || points < 0) {
      toast.error('Level points must be a valid non-negative number.');
      return;
    }

    setIsSavingLevel(true);
    try {
      const next = await addAssignmentTeacherCriterionLevel(assignmentId, criterion.id, {
        label,
        description: draft.description.trim(),
        points,
      });
      onContentChange(next);
      setDraft(EMPTY_LEVEL);
      toast.success('Teacher rubric level added.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to add rubric level.'));
    } finally {
      setIsSavingLevel(false);
    }
  }

  async function moveLevel(levelIndex: number, direction: -1 | 1) {
    const currentOrder = criterion.levels.map((level) => level.id);
    const nextOrder = moveItem(currentOrder, levelIndex, levelIndex + direction);
    if (nextOrder.join(',') === currentOrder.join(',')) return;

    setIsMovingLevels(true);
    try {
      const next = await reorderAssignmentTeacherCriterionLevels(
        assignmentId,
        criterion.id,
        nextOrder,
      );
      onContentChange(next);
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to reorder rubric levels.'));
    } finally {
      setIsMovingLevels(false);
    }
  }

  async function handleSaveCriterion() {
    const title = criterionDraft.title.trim();
    const weight = Number(criterionDraft.weight);
    if (!title) {
      toast.error('Criterion title is required.');
      return;
    }
    if (!Number.isFinite(weight) || weight <= 0) {
      toast.error('Criterion weight must be greater than zero.');
      return;
    }

    setIsSavingCriterion(true);
    try {
      const next = await updateAssignmentTeacherCriterion(assignmentId, criterion.id, {
        title,
        description: criterionDraft.description.trim(),
        weight,
      });
      onContentChange(next);
      setIsEditingCriterion(false);
      toast.success('Teacher criterion updated.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to update criterion.'));
    } finally {
      setIsSavingCriterion(false);
    }
  }

  async function handleDeleteCriterion() {
    if (!confirmDestructiveAction('Remove this teacher-added criterion and its levels?')) {
      return;
    }
    setIsDeletingCriterion(true);
    try {
      const next = await deleteAssignmentTeacherCriterion(assignmentId, criterion.id);
      onContentChange(next);
      toast.success('Teacher criterion removed.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to remove criterion.'));
    } finally {
      setIsDeletingCriterion(false);
    }
  }

  async function handleSaveLevel(levelId: number) {
    const label = editingLevelDraft.label.trim();
    const points = Number(editingLevelDraft.points);
    if (!label) {
      toast.error('Level label is required.');
      return;
    }
    if (!Number.isFinite(points) || points < 0) {
      toast.error('Level points must be a valid non-negative number.');
      return;
    }

    setIsSavingLevel(true);
    try {
      const next = await updateAssignmentTeacherCriterionLevel(assignmentId, criterion.id, levelId, {
        label,
        description: editingLevelDraft.description.trim(),
        points,
      });
      onContentChange(next);
      setEditingLevelId(null);
      setEditingLevelDraft(EMPTY_LEVEL);
      toast.success('Teacher rubric level updated.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to update rubric level.'));
    } finally {
      setIsSavingLevel(false);
    }
  }

  async function handleDeleteLevel(levelId: number) {
    if (!confirmDestructiveAction('Remove this teacher-added rubric level?')) {
      return;
    }
    setDeletingLevelId(levelId);
    try {
      const next = await deleteAssignmentTeacherCriterionLevel(assignmentId, criterion.id, levelId);
      onContentChange(next);
      toast.success('Teacher rubric level removed.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to remove rubric level.'));
    } finally {
      setDeletingLevelId(null);
    }
  }

  return (
    <article className="rounded-2xl border border-border/70 bg-background p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-foreground">{criterion.title}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Weight {formatPoints(criterion.weight)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-primary/10 px-2 py-1 text-[11px] font-medium uppercase tracking-wide text-primary">
            Local
          </span>
          <Button
            type="button"
            size="icon"
            variant="outline"
            className="h-8 w-8"
            disabled={!canCompose || isSavingCriterion || isDeletingCriterion}
            onClick={() => setIsEditingCriterion((current) => !current)}
            aria-label={isEditingCriterion ? `Cancel editing ${criterion.title}` : `Edit ${criterion.title}`}
          >
            {isEditingCriterion ? <X className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
          </Button>
          <Button
            type="button"
            size="icon"
            variant="outline"
            className="h-8 w-8 text-destructive hover:text-destructive"
            disabled={
              !canCompose ||
              isSavingCriterion ||
              isDeletingCriterion ||
              isEditingCriterion ||
              editingLevelId !== null
            }
            onClick={() => void handleDeleteCriterion()}
            aria-label={`Remove ${criterion.title}`}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="outline"
            className="h-8 w-8"
            disabled={
              !canCompose ||
              isSavingCriterion ||
              isDeletingCriterion ||
              isEditingCriterion ||
              editingLevelId !== null ||
              !canMoveUp
            }
            onClick={onMoveUp}
            aria-label={`Move ${criterion.title} earlier`}
          >
            <ArrowUp className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="outline"
            className="h-8 w-8"
            disabled={
              !canCompose ||
              isSavingCriterion ||
              isDeletingCriterion ||
              isEditingCriterion ||
              editingLevelId !== null ||
              !canMoveDown
            }
            onClick={onMoveDown}
            aria-label={`Move ${criterion.title} later`}
          >
            <ArrowDown className="h-4 w-4" />
          </Button>
        </div>
      </div>
      {isEditingCriterion && (
        <div className="mt-4 rounded-2xl border border-dashed border-border/80 bg-card px-3 py-3">
          <div className="space-y-2">
            <Label htmlFor={`edit-criterion-title-${criterion.id}`}>Criterion title</Label>
            <Input
              id={`edit-criterion-title-${criterion.id}`}
              value={criterionDraft.title}
              onChange={(event) =>
                setCriterionDraft((current) => ({ ...current, title: event.target.value }))
              }
              disabled={!canCompose || isSavingCriterion}
            />
          </div>
          <div className="mt-3 space-y-2">
            <Label htmlFor={`edit-criterion-description-${criterion.id}`}>Description</Label>
            <Textarea
              id={`edit-criterion-description-${criterion.id}`}
              value={criterionDraft.description}
              onChange={(event) =>
                setCriterionDraft((current) => ({ ...current, description: event.target.value }))
              }
              disabled={!canCompose || isSavingCriterion}
              rows={3}
            />
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-[120px_auto]">
            <div className="space-y-2">
              <Label htmlFor={`edit-criterion-weight-${criterion.id}`}>Weight</Label>
              <Input
                id={`edit-criterion-weight-${criterion.id}`}
                type="number"
                min="0.01"
                step="0.25"
                value={criterionDraft.weight}
                onChange={(event) =>
                  setCriterionDraft((current) => ({ ...current, weight: event.target.value }))
                }
                disabled={!canCompose || isSavingCriterion}
              />
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              disabled={isSavingCriterion}
              onClick={() => {
                setCriterionDraft({
                  title: criterion.title,
                  description: criterion.description,
                  weight: String(criterion.weight),
                });
                setIsEditingCriterion(false);
              }}
            >
              Cancel
            </Button>
            <Button type="button" onClick={() => void handleSaveCriterion()} disabled={isSavingCriterion}>
              <Check className="mr-2 h-4 w-4" />
              Save criterion
            </Button>
          </div>
        </div>
      )}
      {criterion.description && (
        <p className="mt-3 text-sm text-muted-foreground">{criterion.description}</p>
      )}

      <div className="mt-4 space-y-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Teacher-added levels
          </p>
          <div className="mt-3 space-y-2">
            {criterion.levels.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No local levels yet. Add grading bands for this assignment-only criterion.
              </p>
            ) : (
              criterion.levels.map((level, levelIndex) => (
                <div
                  key={level.id}
                  className="flex flex-col gap-3 rounded-2xl border border-border/60 bg-card px-3 py-3 sm:flex-row sm:items-start sm:justify-between"
                >
                  <div className="min-w-0 flex-1">
                    {editingLevelId === level.id ? (
                      <div className="space-y-3">
                        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_120px]">
                          <div className="space-y-2">
                            <Label htmlFor={`edit-level-label-${level.id}`}>Level label</Label>
                            <Input
                              id={`edit-level-label-${level.id}`}
                              value={editingLevelDraft.label}
                              onChange={(event) =>
                                setEditingLevelDraft((current) => ({
                                  ...current,
                                  label: event.target.value,
                                }))
                              }
                              disabled={!canCompose || isSavingLevel}
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor={`edit-level-points-${level.id}`}>Points</Label>
                            <Input
                              id={`edit-level-points-${level.id}`}
                              type="number"
                              min="0"
                              step="0.5"
                              value={editingLevelDraft.points}
                              onChange={(event) =>
                                setEditingLevelDraft((current) => ({
                                  ...current,
                                  points: event.target.value,
                                }))
                              }
                              disabled={!canCompose || isSavingLevel}
                            />
                          </div>
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor={`edit-level-description-${level.id}`}>Description</Label>
                          <Textarea
                            id={`edit-level-description-${level.id}`}
                            value={editingLevelDraft.description}
                            onChange={(event) =>
                              setEditingLevelDraft((current) => ({
                                ...current,
                                description: event.target.value,
                              }))
                            }
                            disabled={!canCompose || isSavingLevel}
                            rows={3}
                          />
                        </div>
                      </div>
                    ) : (
                      <div>
                        <p className="text-sm font-semibold text-foreground">{level.label}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {formatPoints(level.points)} points
                        </p>
                        {level.description && (
                          <p className="mt-2 text-sm text-muted-foreground">{level.description}</p>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 self-start">
                    <Button
                      type="button"
                      size="icon"
                      variant="outline"
                      className="h-8 w-8"
                      disabled={!canCompose || isSavingLevel || deletingLevelId === level.id}
                      onClick={() => {
                        if (editingLevelId === level.id) {
                          setEditingLevelId(null);
                          setEditingLevelDraft(EMPTY_LEVEL);
                          return;
                        }
                        setEditingLevelId(level.id);
                        setEditingLevelDraft({
                          label: level.label,
                          description: level.description,
                          points: String(level.points),
                        });
                      }}
                      aria-label={
                        editingLevelId === level.id
                          ? `Cancel editing ${level.label}`
                          : `Edit ${level.label}`
                      }
                    >
                      {editingLevelId === level.id ? (
                        <X className="h-4 w-4" />
                      ) : (
                        <Pencil className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      type="button"
                      size="icon"
                      variant="outline"
                      className="h-8 w-8 text-destructive hover:text-destructive"
                      disabled={
                        !canCompose ||
                        isSavingLevel ||
                        deletingLevelId === level.id ||
                        (editingLevelId !== null && editingLevelId !== level.id)
                      }
                      onClick={() => void handleDeleteLevel(level.id)}
                      aria-label={`Remove ${level.label}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="icon"
                      variant="outline"
                      className="h-8 w-8"
                      disabled={
                        !canCompose ||
                        isMovingLevels ||
                        isSavingLevel ||
                        deletingLevelId === level.id ||
                        editingLevelId === level.id ||
                        levelIndex === 0
                      }
                      onClick={() => void moveLevel(levelIndex, -1)}
                      aria-label={`Move ${level.label} earlier`}
                    >
                      <ArrowUp className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="icon"
                      variant="outline"
                      className="h-8 w-8"
                      disabled={
                        !canCompose ||
                        isMovingLevels ||
                        isSavingLevel ||
                        deletingLevelId === level.id ||
                        editingLevelId === level.id ||
                        levelIndex === criterion.levels.length - 1
                      }
                      onClick={() => void moveLevel(levelIndex, 1)}
                      aria-label={`Move ${level.label} later`}
                    >
                      <ArrowDown className="h-4 w-4" />
                    </Button>
                    {editingLevelId === level.id && (
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={!canCompose || isSavingLevel}
                        onClick={() => void handleSaveLevel(level.id)}
                      >
                        <Check className="mr-2 h-4 w-4" />
                        Save
                      </Button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-dashed border-border/80 bg-card px-3 py-3">
          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_120px]">
            <div className="space-y-2">
              <Label htmlFor={`criterion-level-label-${criterion.id}`}>Level label</Label>
              <Input
                id={`criterion-level-label-${criterion.id}`}
                value={draft.label}
                onChange={(event) => setDraft((current) => ({ ...current, label: event.target.value }))}
                disabled={!canCompose || isSavingLevel}
                placeholder="Exceeds expectations"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={`criterion-level-points-${criterion.id}`}>Points</Label>
              <Input
                id={`criterion-level-points-${criterion.id}`}
                type="number"
                min="0"
                step="0.5"
                value={draft.points}
                onChange={(event) => setDraft((current) => ({ ...current, points: event.target.value }))}
                disabled={!canCompose || isSavingLevel}
              />
            </div>
          </div>
          <div className="mt-3 space-y-2">
            <Label htmlFor={`criterion-level-description-${criterion.id}`}>Description</Label>
            <Textarea
              id={`criterion-level-description-${criterion.id}`}
              value={draft.description}
              onChange={(event) =>
                setDraft((current) => ({ ...current, description: event.target.value }))
              }
              disabled={!canCompose || isSavingLevel}
              rows={3}
              placeholder="Describe what this band should look like."
            />
          </div>
          <div className="mt-3 flex justify-end">
            <Button
              type="button"
              variant="secondary"
              onClick={() => void handleAddLevel()}
              disabled={!canCompose || isSavingLevel || editingLevelId !== null || isEditingCriterion}
            >
              <Plus className="mr-2 h-4 w-4" />
              Add level
            </Button>
          </div>
        </div>
      </div>
    </article>
  );
}

export default function AssignmentComposerPanel({
  assignmentId,
  content,
  canCompose,
  onContentChange,
}: Props) {
  const [questionDraft, setQuestionDraft] = useState<QuestionDraft>(makeEmptyQuestionDraft());
  const [criterionDraft, setCriterionDraft] = useState<CriterionDraft>(EMPTY_CRITERION);
  const [selectedQuestion, setSelectedQuestion] = useState<SelectedQuestionState>(null);
  const [isSavingQuestion, setIsSavingQuestion] = useState(false);
  const [isSavingCriterion, setIsSavingCriterion] = useState(false);
  const [isReorderingQuestions, setIsReorderingQuestions] = useState(false);
  const [isReorderingCriteria, setIsReorderingCriteria] = useState(false);
  const [templateRubric, setTemplateRubric] = useState<Rubric | null>(null);
  const [isLoadingRubric, setIsLoadingRubric] = useState(false);
  const [mobileView, setMobileView] = useState<'structure' | 'editor' | 'settings'>('editor');
  const [showLockedRubric, setShowLockedRubric] = useState(false);

  const inheritedQuestions = useMemo(
    () => content.questions.filter((question) => question.origin === 'TEMPLATE'),
    [content.questions],
  );
  const teacherQuestions = useMemo(
    () => content.questions.filter((question) => question.origin === 'TEACHER_ADDITION'),
    [content.questions],
  );
  const activeQuestion = useMemo(
    () =>
      selectedQuestion && selectedQuestion !== 'new'
        ? content.questions.find((question) => question.id === selectedQuestion) ?? null
        : null,
    [content.questions, selectedQuestion],
  );
  const combinedRubricCriteria = useMemo(
    () => [...(templateRubric?.criteria ?? []), ...content.teacherCriteria],
    [content.teacherCriteria, templateRubric],
  );

  function updateTeacherQuestionImage(
    questionId: number,
    image: AssignmentQuestion['image'],
  ) {
    onContentChange({
      ...content,
      questions: content.questions.map((question) =>
        question.id === questionId ? { ...question, image } : question,
      ),
    });
  }

  useEffect(() => {
    if (!content.rubricId) {
      setTemplateRubric(null);
      return;
    }

    let active = true;
    setIsLoadingRubric(true);
    getRubric(content.rubricId)
      .then((rubric) => {
        if (!active) return;
        setTemplateRubric(rubric);
      })
      .catch(() => {
        if (!active) return;
        setTemplateRubric(null);
      })
      .finally(() => {
        if (!active) return;
        setIsLoadingRubric(false);
      });

    return () => {
      active = false;
    };
  }, [content.rubricId]);

  useEffect(() => {
    if (selectedQuestion === 'new') return;
    if (selectedQuestion && content.questions.some((question) => question.id === selectedQuestion)) {
      return;
    }
    const nextSelection = content.questions[0]?.id ?? null;
    setSelectedQuestion(nextSelection);
  }, [content.questions, selectedQuestion, teacherQuestions]);

  useEffect(() => {
    if (activeQuestion && activeQuestion.origin === 'TEACHER_ADDITION') {
      setQuestionDraft(toQuestionDraft(activeQuestion));
    }
  }, [activeQuestion]);

  async function handleAddQuestion() {
    const prompt = questionDraft.prompt.trim();
    const maxPoints = Number(questionDraft.maxPoints);
    if (!prompt) {
      toast.error('Question prompt is required.');
      return;
    }
    if (!Number.isFinite(maxPoints) || maxPoints < 0) {
      toast.error('Max points must be a valid non-negative number.');
      return;
    }

    setIsSavingQuestion(true);
    try {
      const next = await addAssignmentQuestion(assignmentId, {
        type: questionDraft.type,
        prompt,
        maxPoints,
        data: questionDraft.data,
      });
      onContentChange(next);
      setQuestionDraft(makeEmptyQuestionDraft());
      const nextTeacherQuestion =
        next.questions.filter((question) => question.origin === 'TEACHER_ADDITION').at(-1) ?? null;
      setSelectedQuestion(nextTeacherQuestion?.id ?? null);
      toast.success('Assignment question added.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to add question.'));
    } finally {
      setIsSavingQuestion(false);
    }
  }

  async function handleAddCriterion() {
    const title = criterionDraft.title.trim();
    const weight = Number(criterionDraft.weight);
    if (!title) {
      toast.error('Criterion title is required.');
      return;
    }
    if (!Number.isFinite(weight) || weight <= 0) {
      toast.error('Criterion weight must be greater than zero.');
      return;
    }

    setIsSavingCriterion(true);
    try {
      const next = await addAssignmentTeacherCriterion(assignmentId, {
        title,
        description: criterionDraft.description.trim(),
        weight,
      });
      onContentChange(next);
      setCriterionDraft(EMPTY_CRITERION);
      toast.success('Teacher criterion added.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to add criterion.'));
    } finally {
      setIsSavingCriterion(false);
    }
  }

  async function moveTeacherQuestion(questionIndex: number, direction: -1 | 1) {
    const nextQuestions = moveItem(
      teacherQuestions.map((question) => question.id),
      questionIndex,
      questionIndex + direction,
    );

    setIsReorderingQuestions(true);
    try {
      const next = await reorderAssignmentQuestions(assignmentId, nextQuestions);
      onContentChange(next);
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to reorder teacher questions.'));
    } finally {
      setIsReorderingQuestions(false);
    }
  }

  async function moveTeacherCriterion(criterionIndex: number, direction: -1 | 1) {
    const nextCriteria = moveItem(
      content.teacherCriteria.map((criterion) => criterion.id),
      criterionIndex,
      criterionIndex + direction,
    );

    setIsReorderingCriteria(true);
    try {
      const next = await reorderAssignmentTeacherCriteria(assignmentId, nextCriteria);
      onContentChange(next);
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to reorder teacher criteria.'));
    } finally {
      setIsReorderingCriteria(false);
    }
  }

  const activeTeacherQuestion =
    activeQuestion && activeQuestion.origin === 'TEACHER_ADDITION' ? activeQuestion : null;
  const activeTeacherQuestionIndex =
    activeTeacherQuestion == null
      ? -1
      : teacherQuestions.findIndex((question) => question.id === activeTeacherQuestion.id);

  return (
    <section className="flex h-[calc(100vh-64px)] flex-col overflow-hidden rounded-2xl border border-border bg-background">
      <div className="flex border-b border-border bg-muted/30 lg:hidden">
        {(
          [
            { key: 'structure', label: 'Structure' },
            { key: 'editor', label: 'Editor' },
            { key: 'settings', label: 'Rubric' },
          ] as const
        ).map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setMobileView(tab.key)}
            className={cn(
              'flex-1 py-2.5 text-[10px] font-bold uppercase tracking-widest transition-colors',
              mobileView === tab.key
                ? 'border-b-2 border-primary bg-card text-foreground'
                : 'text-muted-foreground',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="relative flex flex-1 overflow-hidden">
        <aside
          className={cn(
            'flex w-[320px] shrink-0 flex-col overflow-hidden border-r border-border bg-muted/30 transition-transform duration-200',
            'max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:z-20 max-lg:w-full max-lg:bg-background',
            mobileView === 'structure'
              ? 'max-lg:translate-x-0'
              : 'max-lg:-translate-x-full lg:translate-x-0',
          )}
        >
          <QuestionRail
            questions={content.questions}
            selectedQuestion={selectedQuestion}
            canCompose={canCompose}
            onSelectQuestion={(questionId) => {
              setSelectedQuestion(questionId);
              setMobileView('editor');
            }}
            onStartNewQuestion={() => {
              if (!canCompose) return;
              setQuestionDraft(makeEmptyQuestionDraft());
              setSelectedQuestion('new');
              setMobileView('editor');
            }}
            onBackToEditor={() => setMobileView('editor')}
          />
        </aside>

        <main
          className={cn(
            'flex-1 overflow-y-auto bg-background transition-opacity duration-200',
            mobileView !== 'editor' && 'max-lg:hidden',
          )}
        >
          <div className="px-4 py-4 lg:px-6">
            {selectedQuestion === 'new' ? (
          <NewQuestionStudio
            draft={questionDraft}
            canCompose={canCompose && !isSavingQuestion}
            onDraftChange={setQuestionDraft}
            onCreate={() => void handleAddQuestion()}
          />
        ) : activeTeacherQuestion ? (
          <TeacherQuestionStudio
            assignmentId={assignmentId}
            question={activeTeacherQuestion}
            draft={questionDraft}
            canCompose={canCompose && !isReorderingQuestions}
            canMoveUp={activeTeacherQuestionIndex > 0}
            canMoveDown={activeTeacherQuestionIndex < teacherQuestions.length - 1}
            activeImage={activeTeacherQuestion.image}
            isSaving={isSavingQuestion}
            isDeleting={false}
            onDraftChange={setQuestionDraft}
            onMoveUp={() => void moveTeacherQuestion(activeTeacherQuestionIndex, -1)}
            onMoveDown={() => void moveTeacherQuestion(activeTeacherQuestionIndex, 1)}
            onSave={async () => {
              const prompt = questionDraft.prompt.trim();
              const maxPoints = Number(questionDraft.maxPoints);
              if (!prompt) {
                toast.error('Question prompt is required.');
                return;
              }
              if (!Number.isFinite(maxPoints) || maxPoints < 0) {
                toast.error('Max points must be a valid non-negative number.');
                return;
              }

              setIsSavingQuestion(true);
              try {
                const next = await updateAssignmentQuestion(assignmentId, activeTeacherQuestion.id, {
                  type: questionDraft.type,
                  prompt,
                  maxPoints,
                  data: questionDraft.data,
                });
                onContentChange(next);
                toast.success('Assignment question updated.');
              } catch (error: unknown) {
                toast.error(toErrorMessage(error, 'Failed to update question.'));
              } finally {
                setIsSavingQuestion(false);
              }
            }}
            onDelete={async () => {
              if (!confirmDestructiveAction('Remove this teacher-added question from the assignment?')) {
                return;
              }
              setIsSavingQuestion(true);
              try {
                const next = await deleteAssignmentQuestion(assignmentId, activeTeacherQuestion.id);
                onContentChange(next);
                const nextTeacherQuestion =
                  next.questions.find((question) => question.origin === 'TEACHER_ADDITION') ??
                  next.questions[0] ??
                  null;
                setSelectedQuestion(nextTeacherQuestion?.id ?? null);
                toast.success('Assignment question removed.');
              } catch (error: unknown) {
                toast.error(toErrorMessage(error, 'Failed to remove question.'));
              } finally {
                setIsSavingQuestion(false);
              }
            }}
            onImageChange={(nextImage) =>
              updateTeacherQuestionImage(activeTeacherQuestion.id, nextImage)
            }
          />
        ) : activeQuestion ? (
          <LockedQuestionStudio question={activeQuestion} />
        ) : (
          <section className="rounded-3xl border border-border bg-card px-5 py-12 text-center shadow-sm">
            <div className="mx-auto flex max-w-md flex-col items-center">
              <div className="rounded-full bg-muted p-3 text-muted-foreground">
                <FileText className="h-6 w-6" />
              </div>
              <h2 className="mt-4 text-xl font-semibold text-foreground">Select a question</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Pick a locked researcher question to review it, or start a new local question from
                the structure rail.
              </p>
            </div>
          </section>
        )}
          </div>
        </main>

        <aside
          className={cn(
            'w-[360px] shrink-0 overflow-y-auto border-l border-border bg-muted/30 transition-transform duration-200 xl:w-[380px]',
            'max-lg:fixed max-lg:inset-y-0 max-lg:right-0 max-lg:z-20 max-lg:w-full max-lg:bg-background',
            mobileView === 'settings'
              ? 'max-lg:translate-x-0'
              : 'max-lg:translate-x-full lg:translate-x-0',
          )}
        >
          <div className="flex flex-col gap-6 p-4">
            <div className="lg:hidden -m-4 mb-2 flex items-center justify-between border-b border-border bg-card p-3">
              <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                Rubric
              </span>
              <Button type="button" variant="ghost" size="sm" onClick={() => setMobileView('editor')}>
                Back
              </Button>
            </div>

            <section className="rounded-3xl border border-border bg-card p-5 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Rubric
              </p>
              <h2 className="mt-2 text-xl font-semibold text-foreground">Assignment rubric</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Shared rubric criteria stay fixed. Add your own criteria or levels here for this assignment.
              </p>

              <div className="mt-5 rounded-2xl border border-dashed border-border/80 bg-background p-4 space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="assignment-criterion-title">Criterion title</Label>
                  <Input
                    id="assignment-criterion-title"
                    value={criterionDraft.title}
                    onChange={(event) =>
                      setCriterionDraft((current) => ({
                        ...current,
                        title: event.target.value,
                      }))
                    }
                    disabled={!canCompose || isSavingCriterion}
                    placeholder="Add an assignment-only criterion"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="assignment-criterion-description">Description</Label>
                  <Textarea
                    id="assignment-criterion-description"
                    value={criterionDraft.description}
                    onChange={(event) =>
                      setCriterionDraft((current) => ({
                        ...current,
                        description: event.target.value,
                      }))
                    }
                    disabled={!canCompose || isSavingCriterion}
                    placeholder="Explain how this local criterion should be used."
                    rows={4}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="assignment-criterion-weight">Weight</Label>
                  <Input
                    id="assignment-criterion-weight"
                    type="number"
                    min="0.01"
                    step="0.25"
                    value={criterionDraft.weight}
                    onChange={(event) =>
                      setCriterionDraft((current) => ({
                        ...current,
                        weight: event.target.value,
                      }))
                    }
                    disabled={!canCompose || isSavingCriterion}
                  />
                </div>
                <div className="pt-1">
                  <Button
                    type="button"
                    className="w-full"
                    onClick={() => void handleAddCriterion()}
                    disabled={!canCompose || isSavingCriterion}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Add criterion
                  </Button>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {content.teacherCriteria.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No assignment-only criteria yet.</p>
                ) : (
                  content.teacherCriteria.map((criterion) => (
                    <TeacherCriterionCard
                      key={criterion.id}
                      assignmentId={assignmentId}
                      criterion={criterion}
                      canCompose={canCompose && !isReorderingCriteria}
                      canMoveUp={content.teacherCriteria.findIndex((item) => item.id === criterion.id) > 0}
                      canMoveDown={
                        content.teacherCriteria.findIndex((item) => item.id === criterion.id) <
                        content.teacherCriteria.length - 1
                      }
                      onMoveUp={() =>
                        void moveTeacherCriterion(
                          content.teacherCriteria.findIndex((item) => item.id === criterion.id),
                          -1,
                        )
                      }
                      onMoveDown={() =>
                        void moveTeacherCriterion(
                          content.teacherCriteria.findIndex((item) => item.id === criterion.id),
                          1,
                        )
                      }
                      onContentChange={onContentChange}
                    />
                  ))
                )}
              </div>

              <div className="mt-5 rounded-2xl border border-border/70 bg-background p-4">
                <RubricGridPreview
                  criteria={combinedRubricCriteria}
                  title="Rubric preview"
                />
              </div>

              <div className="mt-5 rounded-2xl border border-border/70 bg-background">
                <button
                  type="button"
                  onClick={() => setShowLockedRubric((current) => !current)}
                  className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
                >
                  <div>
                    <p className="text-sm font-medium text-foreground">Shared rubric</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Review the locked rubric that came from the shared template.
                    </p>
                  </div>
                  {showLockedRubric ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>
                {showLockedRubric ? (
                  <div className="border-t border-border/70 px-4 py-4">
                    {!content.rubricId ? (
                      <p className="text-sm text-foreground">No template rubric attached.</p>
                    ) : isLoadingRubric ? (
                      <p className="text-sm text-muted-foreground">Loading locked rubric…</p>
                    ) : templateRubric ? (
                      <InheritedRubricList rubric={templateRubric} />
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        Template rubric #{content.rubricId} is attached but could not be loaded.
                      </p>
                    )}
                  </div>
                ) : null}
              </div>
            </section>
          </div>
        </aside>
      </div>
    </section>
  );
}
