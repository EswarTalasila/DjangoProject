'use client';

import { useEffect, useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, Check, Lock, Pencil, Plus, Sparkles, Trash2, X } from 'lucide-react';
import { toast } from 'sonner';

import ImagePicker from '@/components/media/ImagePicker';
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
  deleteAssignmentTeacherCriterion,
  deleteAssignmentTeacherCriterionLevel,
  deleteAssignmentQuestionImage,
  listReusableAssignmentImages,
  reorderAssignmentQuestions,
  reorderAssignmentTeacherCriteria,
  reorderAssignmentTeacherCriterionLevels,
  reuseAssignmentQuestionImage,
  uploadAssignmentQuestionImage,
  updateAssignmentQuestion,
  updateAssignmentTeacherCriterion,
  updateAssignmentTeacherCriterionLevel,
  type AssignmentContent,
  type AssignmentQuestion,
  type AssignmentTeacherCriterion,
} from '@/lib/assignment-api';
import type { QuestionData, QuestionKind } from '@/lib/assignment-template-api';
import { getRubric, type Rubric } from '@/lib/rubric-api';
import { toErrorMessage } from '@/lib/utils';

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

const EMPTY_QUESTION: QuestionDraft = {
  type: 'SHORT_ANSWER',
  prompt: '',
  maxPoints: '1',
};

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
  return undefined;
}

function confirmDestructiveAction(message: string): boolean {
  if (typeof window === 'undefined' || typeof window.confirm !== 'function') {
    return true;
  }
  return window.confirm(message);
}

function InheritedQuestionCard({ question }: { question: AssignmentQuestion }) {
  return (
    <article className="rounded-2xl border border-border/70 bg-background p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              <Lock className="h-3 w-3" />
              Locked template
            </span>
            <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
              {question.type.replaceAll('_', ' ')}
            </span>
          </div>
          <h3 className="text-sm font-semibold text-foreground">{question.prompt}</h3>
          <p className="text-xs text-muted-foreground">{formatPoints(question.maxPoints)} points</p>
        </div>
      </div>
      {question.image && (
        <div className="mt-4 overflow-hidden rounded-xl border border-border/60">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={question.image.url}
            alt={question.image.originalFilename}
            className="h-44 w-full object-cover"
          />
        </div>
      )}
    </article>
  );
}

function TeacherQuestionCard({
  assignmentId,
  question,
  canCompose,
  canMoveUp,
  canMoveDown,
  onMoveUp,
  onMoveDown,
  onContentChange,
}: {
  assignmentId: number;
  question: AssignmentQuestion;
  canCompose: boolean;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onContentChange: (next: AssignmentContent) => void;
}) {
  const [image, setImage] = useState(question.image);
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState<QuestionDraft>({
    type: question.type,
    prompt: question.prompt,
    maxPoints: String(question.maxPoints),
  });
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    setImage(question.image);
    setDraft({
      type: question.type,
      prompt: question.prompt,
      maxPoints: String(question.maxPoints),
    });
  }, [question]);

  async function handleSave() {
    const prompt = draft.prompt.trim();
    const maxPoints = Number(draft.maxPoints);
    if (!prompt) {
      toast.error('Question prompt is required.');
      return;
    }
    if (!Number.isFinite(maxPoints) || maxPoints < 0) {
      toast.error('Max points must be a valid non-negative number.');
      return;
    }

    setIsSaving(true);
    try {
      const next = await updateAssignmentQuestion(assignmentId, question.id, {
        type: draft.type,
        prompt,
        maxPoints,
        data:
          draft.type === question.type
            ? (question.data ?? buildQuestionData(draft.type))
            : buildQuestionData(draft.type),
      });
      onContentChange(next);
      setIsEditing(false);
      toast.success('Assignment question updated.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to update question.'));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirmDestructiveAction('Remove this teacher-added question from the assignment?')) {
      return;
    }
    setIsDeleting(true);
    try {
      const next = await deleteAssignmentQuestion(assignmentId, question.id);
      onContentChange(next);
      toast.success('Assignment question removed.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to remove question.'));
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <article className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-1 text-[11px] font-medium uppercase tracking-wide text-primary">
            <Sparkles className="h-3 w-3" />
            Teacher added
          </span>
          <h3 className="text-sm font-semibold text-foreground">{question.prompt}</h3>
          <p className="text-xs text-muted-foreground">
            {question.type.replaceAll('_', ' ')} • {formatPoints(question.maxPoints)} points
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            size="icon"
            variant="outline"
            className="h-8 w-8"
            disabled={!canCompose || isSaving || isDeleting}
            onClick={() => setIsEditing((current) => !current)}
            aria-label={isEditing ? `Cancel editing ${question.prompt}` : `Edit ${question.prompt}`}
          >
            {isEditing ? <X className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
          </Button>
          <Button
            type="button"
            size="icon"
            variant="outline"
            className="h-8 w-8 text-destructive hover:text-destructive"
            disabled={!canCompose || isSaving || isDeleting || isEditing}
            onClick={() => void handleDelete()}
            aria-label={`Remove ${question.prompt}`}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="outline"
            className="h-8 w-8"
            disabled={!canCompose || isSaving || isDeleting || isEditing || !canMoveUp}
            onClick={onMoveUp}
            aria-label={`Move ${question.prompt} earlier`}
          >
            <ArrowUp className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="outline"
            className="h-8 w-8"
            disabled={!canCompose || isSaving || isDeleting || isEditing || !canMoveDown}
            onClick={onMoveDown}
            aria-label={`Move ${question.prompt} later`}
          >
            <ArrowDown className="h-4 w-4" />
          </Button>
        </div>
      </div>
      {isEditing && (
        <div className="mt-4 rounded-2xl border border-dashed border-border/80 bg-background p-4">
          <div className="grid gap-3 md:grid-cols-[160px_minmax(0,1fr)_140px]">
            <div className="space-y-2">
              <Label htmlFor={`edit-question-type-${question.id}`}>Type</Label>
              <Select
                value={draft.type}
                onValueChange={(value) =>
                  setDraft((current) => ({ ...current, type: value as QuestionKind }))
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
              <Input
                id={`edit-question-prompt-${question.id}`}
                value={draft.prompt}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, prompt: event.target.value }))
                }
                disabled={!canCompose || isSaving}
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
                onChange={(event) =>
                  setDraft((current) => ({ ...current, maxPoints: event.target.value }))
                }
                disabled={!canCompose || isSaving}
              />
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              disabled={isSaving}
              onClick={() => {
                setDraft({
                  type: question.type,
                  prompt: question.prompt,
                  maxPoints: String(question.maxPoints),
                });
                setIsEditing(false);
              }}
            >
              Cancel
            </Button>
            <Button type="button" onClick={() => void handleSave()} disabled={isSaving}>
              <Check className="mr-2 h-4 w-4" />
              Save question
            </Button>
          </div>
        </div>
      )}
      <div className="mt-4">
        <ImagePicker
          image={image}
          disabled={!canCompose || isSaving || isDeleting}
          emptyLabel="Attach a supporting image"
          emptyHint="Reuse an earlier question image or upload a new one."
          browseLabel="Reuse Existing Image"
          browseDialogTitle="Choose a reusable question image"
          onBrowse={() => listReusableAssignmentImages(assignmentId)}
          onUpload={async (file) => {
            const next = await uploadAssignmentQuestionImage(assignmentId, question.id, file);
            setImage(next);
            toast.success('Question image uploaded.');
            return next;
          }}
          onSelect={async (picked) => {
            const next = await reuseAssignmentQuestionImage(assignmentId, question.id, picked.id);
            setImage(next);
            toast.success('Question image attached.');
          }}
          onRemove={async () => {
            await deleteAssignmentQuestionImage(assignmentId, question.id);
            setImage(null);
            toast.success('Question image removed.');
          }}
        />
      </div>
    </article>
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
  const [questionDraft, setQuestionDraft] = useState<QuestionDraft>(EMPTY_QUESTION);
  const [criterionDraft, setCriterionDraft] = useState<CriterionDraft>(EMPTY_CRITERION);
  const [isSavingQuestion, setIsSavingQuestion] = useState(false);
  const [isSavingCriterion, setIsSavingCriterion] = useState(false);
  const [isReorderingQuestions, setIsReorderingQuestions] = useState(false);
  const [isReorderingCriteria, setIsReorderingCriteria] = useState(false);
  const [templateRubric, setTemplateRubric] = useState<Rubric | null>(null);
  const [isLoadingRubric, setIsLoadingRubric] = useState(false);

  const inheritedQuestions = useMemo(
    () => content.questions.filter((question) => question.origin === 'TEMPLATE'),
    [content.questions],
  );
  const teacherQuestions = useMemo(
    () => content.questions.filter((question) => question.origin === 'TEACHER_ADDITION'),
    [content.questions],
  );

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
        data: buildQuestionData(questionDraft.type),
      });
      onContentChange(next);
      setQuestionDraft(EMPTY_QUESTION);
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

  return (
    <section className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.85fr)]">
      <div className="space-y-6">
        <div className="rounded-3xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Researcher Template
              </p>
              <h2 className="mt-2 text-xl font-semibold text-foreground">
                Locked source content
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Teachers can review inherited prompts and visuals, but cannot change what the
                researcher published.
              </p>
            </div>
            <div className="rounded-2xl border border-border/70 bg-muted/40 px-3 py-2 text-right">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Inherited</p>
              <p className="text-lg font-semibold text-foreground">{inheritedQuestions.length}</p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {inheritedQuestions.length === 0 ? (
              <p className="text-sm text-muted-foreground">No inherited questions in this template.</p>
            ) : (
              inheritedQuestions.map((question) => (
                <InheritedQuestionCard key={question.id} question={question} />
              ))
            )}
          </div>
        </div>

        <div className="rounded-3xl border border-border bg-card p-5 shadow-sm">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Teacher Additions
            </p>
            <h2 className="mt-2 text-xl font-semibold text-foreground">Assignment-only questions</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Add local prompts and supporting images without changing the researcher template.
            </p>
          </div>

          <div className="mt-5 rounded-2xl border border-dashed border-border/80 bg-background p-4">
            <div className="grid gap-3 md:grid-cols-[160px_minmax(0,1fr)_140px_auto]">
              <div className="space-y-2">
                <Label htmlFor="assignment-question-type">Type</Label>
                <Select
                  value={questionDraft.type}
                  onValueChange={(value) =>
                    setQuestionDraft((current) => ({
                      ...current,
                      type: value as QuestionKind,
                    }))
                  }
                  disabled={!canCompose || isSavingQuestion}
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
                <Input
                  id="assignment-question-prompt"
                  value={questionDraft.prompt}
                  onChange={(event) =>
                    setQuestionDraft((current) => ({
                      ...current,
                      prompt: event.target.value,
                    }))
                  }
                  disabled={!canCompose || isSavingQuestion}
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
                  value={questionDraft.maxPoints}
                  onChange={(event) =>
                    setQuestionDraft((current) => ({
                      ...current,
                      maxPoints: event.target.value,
                    }))
                  }
                  disabled={!canCompose || isSavingQuestion}
                />
              </div>
              <div className="flex items-end">
                <Button
                  type="button"
                  className="w-full"
                  onClick={() => void handleAddQuestion()}
                  disabled={!canCompose || isSavingQuestion}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add
                </Button>
              </div>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {teacherQuestions.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No teacher-added questions yet. Add local prompts here instead of editing the
                researcher template.
              </p>
            ) : (
              teacherQuestions.map((question) => (
                <TeacherQuestionCard
                  key={question.id}
                  assignmentId={assignmentId}
                  question={question}
                  canCompose={canCompose && !isReorderingQuestions}
                  onContentChange={onContentChange}
                  canMoveUp={teacherQuestions.findIndex((item) => item.id === question.id) > 0}
                  canMoveDown={
                    teacherQuestions.findIndex((item) => item.id === question.id) <
                    teacherQuestions.length - 1
                  }
                  onMoveUp={() =>
                    void moveTeacherQuestion(
                      teacherQuestions.findIndex((item) => item.id === question.id),
                      -1,
                    )
                  }
                  onMoveDown={() =>
                    void moveTeacherQuestion(
                      teacherQuestions.findIndex((item) => item.id === question.id),
                      1,
                    )
                  }
                />
              ))
            )}
          </div>
        </div>
      </div>

      <aside className="space-y-6">
        <div className="rounded-3xl border border-border bg-card p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Rubric Context
          </p>
          <h2 className="mt-2 text-xl font-semibold text-foreground">Template rubric stays locked</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Teachers cannot edit researcher criteria. Add assignment-only criteria below when you
            need extra grading context.
          </p>

          <div className="mt-4 rounded-2xl border border-border/70 bg-background p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Template rubric</p>
            {!content.rubricId ? (
              <p className="mt-2 text-sm text-foreground">No template rubric attached.</p>
            ) : isLoadingRubric ? (
              <p className="mt-2 text-sm text-muted-foreground">Loading locked rubric…</p>
            ) : templateRubric ? (
              <div className="mt-3 space-y-3">
                <div>
                  <p className="text-sm font-semibold text-foreground">{templateRubric.title}</p>
                  {templateRubric.description && (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {templateRubric.description}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  {templateRubric.criteria.map((criterion) => (
                    <article
                      key={criterion.id}
                      className="rounded-2xl border border-border/60 bg-card px-3 py-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-foreground">
                            {criterion.title}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            Weight {formatPoints(criterion.weight)}
                          </p>
                        </div>
                        <span className="rounded-full bg-muted px-2 py-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                          Locked
                        </span>
                      </div>
                      {criterion.description && (
                        <p className="mt-3 text-sm text-muted-foreground">
                          {criterion.description}
                        </p>
                      )}
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">
                Template rubric #{content.rubricId} is attached but could not be loaded.
              </p>
            )}
          </div>

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
            <div className="grid gap-3 md:grid-cols-[120px_auto]">
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
              <div className="flex items-end">
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
          </div>

          <div className="mt-5 space-y-3">
            {content.teacherCriteria.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No assignment-only criteria yet.
              </p>
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
        </div>
      </aside>
    </section>
  );
}
