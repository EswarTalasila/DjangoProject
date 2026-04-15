'use client';

import { useEffect, useMemo, useState } from 'react';
import { Lock, Plus, Sparkles } from 'lucide-react';
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
  deleteAssignmentQuestionImage,
  listReusableAssignmentImages,
  reuseAssignmentQuestionImage,
  uploadAssignmentQuestionImage,
  type AssignmentContent,
  type AssignmentQuestion,
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
}: {
  assignmentId: number;
  question: AssignmentQuestion;
  canCompose: boolean;
}) {
  const [image, setImage] = useState(question.image);

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
      </div>
      <div className="mt-4">
        <ImagePicker
          image={image}
          disabled={!canCompose}
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
                  canCompose={canCompose}
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
                <article
                  key={criterion.id}
                  className="rounded-2xl border border-border/70 bg-background p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-foreground">{criterion.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Weight {formatPoints(criterion.weight)}
                      </p>
                    </div>
                    <span className="rounded-full bg-primary/10 px-2 py-1 text-[11px] font-medium uppercase tracking-wide text-primary">
                      Local
                    </span>
                  </div>
                  {criterion.description && (
                    <p className="mt-3 text-sm text-muted-foreground">{criterion.description}</p>
                  )}
                </article>
              ))
            )}
          </div>
        </div>
      </aside>
    </section>
  );
}
