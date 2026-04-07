'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { StatusBadge } from '@/components/ui/status-badge';
import {
  getSubmission,
  overrideSubmissionScore,
  type AnswerPayload,
  type SubmissionDTO,
} from '@/lib/submission-api';
import { getAssignment, getAssignmentTemplate, type Assignment } from '@/lib/assignment-api';
import type { Assessment, GradingMode, Question, QuestionGroup } from '@/lib/assessment-api';
import { listRubrics, type Rubric } from '@/lib/rubric-api';
import RubricGridPreview from '@/components/rubrics/RubricGridPreview';
import { toErrorMessage, formatDate, formatScore, cn } from '@/lib/utils';

type Role = 'ADMIN' | 'TEACHER' | 'RESEARCHER' | 'STUDENT';
type RubricSource = 'Question' | 'Group' | 'Assessment' | 'N/A';

type SubmissionDetailViewProps = {
  submissionId: number;
  viewerRole: Role;
};

function formatQuestionKind(kind: Question['type']): string {
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

function renderAnswer(question: Question | undefined, answer: AnswerPayload): string {
  if (answer.type === 'MULTIPLE_CHOICE') {
    const selected = answer.data?.selected ?? [];
    if (selected.length === 0) return 'No option selected';
    const choices = question?.data?.choices ?? [];
    const labels = selected.map((idx) => choices[idx]?.prompt || `Choice ${idx + 1}`);
    return labels.join(', ');
  }
  if (answer.type === 'SHORT_ANSWER') {
    return answer.data?.text?.trim() || 'No response';
  }
  if (answer.type === 'NUMBER_SCALE') {
    return answer.data?.val == null ? 'No value selected' : String(answer.data.val);
  }
  if (answer.type === 'MOOD_METER') {
    return answer.data?.moodName?.trim() || 'No mood selected';
  }
  if (answer.type === 'FILE_UPLOAD') {
    return answer.data?.originalFilename?.trim() || 'No file uploaded';
  }
  return 'No response';
}

function defaultScoreInput(answer: AnswerPayload): string {
  if (answer.score == null) return '';
  if (Number.isInteger(answer.score)) return String(answer.score);
  return answer.score.toFixed(2).replace(/\.?0+$/, '');
}

function isManualQuestion(question: Question | undefined, gradingMode: GradingMode): boolean {
  if (!question) return false;
  if (gradingMode === 'MANUAL') return true;
  if (gradingMode === 'HYBRID') return question.gradingStrategy === 'MANUAL';
  return false;
}

function getEffectiveRubricMeta(
  question: Question | undefined,
  questionGroups: QuestionGroup[],
  assessmentRubricId: number | null,
  rubricById: Map<number, Rubric>,
): { rubricId: number | null; rubric: Rubric | null; source: RubricSource } {
  if (!question) return { rubricId: null, rubric: null, source: 'N/A' };

  if (question.rubricId != null) {
    return {
      rubricId: question.rubricId,
      rubric: rubricById.get(question.rubricId) ?? null,
      source: 'Question',
    };
  }

  const groupRubricId =
    question.groupId != null
      ? (questionGroups.find((group) => group.id === question.groupId)?.rubricId ?? null)
      : null;

  if (groupRubricId != null) {
    return {
      rubricId: groupRubricId,
      rubric: rubricById.get(groupRubricId) ?? null,
      source: 'Group',
    };
  }

  if (assessmentRubricId != null) {
    return {
      rubricId: assessmentRubricId,
      rubric: rubricById.get(assessmentRubricId) ?? null,
      source: 'Assessment',
    };
  }

  return { rubricId: null, rubric: null, source: 'N/A' };
}

function getSubmissionStatusLabel(status: SubmissionDTO['status']): string {
  switch (status) {
    case 'IN_PROGRESS':
      return 'In Progress';
    case 'SUBMITTED':
      return 'Submitted';
    case 'GRADED':
      return 'Graded';
    case 'NOT_STARTED':
    default:
      return 'Not Started';
  }
}

export default function SubmissionDetailView({ submissionId, viewerRole }: SubmissionDetailViewProps) {
  const [submission, setSubmission] = useState<SubmissionDTO | null>(null);
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [assessmentTemplate, setAssessmentTemplate] = useState<Assessment | null>(null);
  const [rubricById, setRubricById] = useState<Map<number, Rubric>>(new Map());
  const [expandedRubricQuestionIds, setExpandedRubricQuestionIds] = useState<Set<number>>(new Set());
  const [scoreInputs, setScoreInputs] = useState<Record<number, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isSavingScores, setIsSavingScores] = useState(false);

  const canOverride = viewerRole === 'TEACHER' || viewerRole === 'ADMIN';

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const currentSubmission = await getSubmission(submissionId);
      const [assignmentRecord, template, rubrics] = await Promise.all([
        getAssignment(currentSubmission.assignmentId),
        getAssignmentTemplate(currentSubmission.assignmentId),
        listRubrics().catch(() => [] as Rubric[]),
      ]);
      setSubmission(currentSubmission);
      setAssignment(assignmentRecord);
      setAssessmentTemplate(template);
      setRubricById(new Map(rubrics.map((rubric) => [rubric.id, rubric])));

      const nextInputs: Record<number, string> = {};
      for (const answer of currentSubmission.answers) {
        nextInputs[answer.questionId] = defaultScoreInput(answer);
      }
      setScoreInputs(nextInputs);
    } catch (error: unknown) {
      setLoadError(toErrorMessage(error, 'Failed to load submission.'));
    } finally {
      setIsLoading(false);
    }
  }, [submissionId]);

  useEffect(() => {
    setIsLoading(true);
    void load();
  }, [load]);

  const questionsById = useMemo(() => {
    const map = new Map<number, Question>();
    for (const question of assessmentTemplate?.questions ?? []) {
      map.set(question.questionId, question);
    }
    return map;
  }, [assessmentTemplate]);

  const totalPoints = useMemo(() => {
    return (assessmentTemplate?.questions ?? []).reduce((sum, question) => sum + question.maxPoints, 0);
  }, [assessmentTemplate]);

  const gradingMode = assessmentTemplate?.gradingMode ?? 'AUTO';

  const answerRows = useMemo(() => {
    if (!submission || !assessmentTemplate) return [];

    return submission.answers.map((answer, index) => {
      const question = questionsById.get(answer.questionId);
      const manualReview = isManualQuestion(question, gradingMode);
      const rubricMeta = getEffectiveRubricMeta(
        question,
        assessmentTemplate.questionGroups,
        assessmentTemplate.rubricId,
        rubricById,
      );
      const canEdit =
        canOverride &&
        !!question &&
        (gradingMode === 'MANUAL' ||
          (gradingMode === 'HYBRID' && manualReview) ||
          gradingMode === 'AUTO');

      const gradingLabel =
        gradingMode === 'AUTO'
          ? canEdit
            ? 'Auto-scored, override optional'
            : 'Auto-scored'
          : manualReview
            ? 'Manual review required'
            : gradingMode === 'HYBRID'
              ? 'Auto-scored in hybrid mode'
              : 'Manual scoring';

      return {
        answer,
        question,
        index,
        manualReview,
        rubricMeta,
        canEdit,
        gradingLabel,
      };
    });
  }, [submission, assessmentTemplate, questionsById, gradingMode, rubricById, canOverride]);

  const manualReviewCount = answerRows.filter((row) => row.manualReview).length;
  const pendingManualCount = answerRows.filter(
    (row) => row.manualReview && (row.answer.score == null || scoreInputs[row.answer.questionId] === ''),
  ).length;
  const autoScoredCount = answerRows.filter((row) => !row.manualReview && row.answer.score != null).length;

  async function handleSaveScores() {
    if (!submission || !canOverride) return;

    const targetAnswers =
      gradingMode === 'HYBRID'
        ? answerRows.filter((row) => row.manualReview).map((row) => row.answer)
        : submission.answers;

    if (targetAnswers.length === 0) {
      toast.error('No questions require score changes.');
      return;
    }

    const payload: number[] = [];
    let hasChanges = false;
    for (const answer of targetAnswers) {
      const input = scoreInputs[answer.questionId] ?? '';
      const parsed = input.trim() === '' ? (answer.score ?? 0) : Number(input);
      if (Number.isNaN(parsed) || parsed < 0) {
        toast.error('All score values must be valid non-negative numbers.');
        return;
      }
      if (Math.abs(parsed - (answer.score ?? 0)) > 1e-9) {
        hasChanges = true;
      }
      payload.push(parsed);
    }

    if (!hasChanges) {
      toast.message(
        gradingMode === 'AUTO'
          ? 'No score overrides to save.'
          : 'No score changes to save.',
      );
      return;
    }

    setIsSavingScores(true);
    try {
      const updated = await overrideSubmissionScore(submission.id, payload);
      setSubmission(updated);
      const nextInputs: Record<number, string> = {};
      for (const answer of updated.answers) {
        nextInputs[answer.questionId] = defaultScoreInput(answer);
      }
      setScoreInputs(nextInputs);
      toast.success('Scores updated.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to update scores.'));
    } finally {
      setIsSavingScores(false);
    }
  }

  function toggleRubric(questionId: number) {
    setExpandedRubricQuestionIds((prev) => {
      const next = new Set(prev);
      if (next.has(questionId)) {
        next.delete(questionId);
      } else {
        next.add(questionId);
      }
      return next;
    });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (loadError || !submission) {
    return (
      <div className="space-y-6 p-6 w-full max-w-6xl mx-auto">
        <Link
          href="/dashboard/submissions"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Submissions
        </Link>
        <p className="text-sm text-destructive">{loadError ?? 'Submission not found.'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 w-full max-w-6xl mx-auto">
      <Link
        href="/dashboard/submissions"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Submissions
      </Link>

      <section className="rounded-sm border border-border bg-card p-6 space-y-5">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Grade Submission
            </h1>
            <p className="text-muted-foreground">
              {assignment?.title || `Assignment #${submission.assignmentId}`}
            </p>
          </div>
          <StatusBadge status={submission.status} label={getSubmissionStatusLabel(submission.status)} />
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-sm border border-border bg-muted/20 p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Student</p>
            <p className="mt-1 text-sm text-foreground">
              {submission.studentId != null ? `#${submission.studentId}` : '-'}
            </p>
          </div>
          <div className="rounded-sm border border-border bg-muted/20 p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Submitted</p>
            <p className="mt-1 text-sm text-foreground">{formatDate(submission.submittedAt)}</p>
          </div>
          <div className="rounded-sm border border-border bg-muted/20 p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Score</p>
            <p className="mt-1 text-sm text-foreground">
              {formatScore(submission.score)} / {formatScore(totalPoints)}
            </p>
          </div>
          <div className="rounded-sm border border-border bg-muted/20 p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Grading Mode</p>
            <p className="mt-1 text-sm text-foreground">{gradingMode}</p>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-sm border border-border bg-muted/10 p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Manual Review</p>
            <p className="mt-1 text-lg font-semibold text-foreground">{manualReviewCount}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Questions whose scores should be set by a teacher.
            </p>
          </div>
          <div className="rounded-sm border border-border bg-muted/10 p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Pending Manual Scores</p>
            <p className="mt-1 text-lg font-semibold text-foreground">{pendingManualCount}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Manual items still missing a score entry.
            </p>
          </div>
          <div className="rounded-sm border border-border bg-muted/10 p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Auto-scored</p>
            <p className="mt-1 text-lg font-semibold text-foreground">{autoScoredCount}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Questions already scored by the system.
            </p>
          </div>
        </div>

        {canOverride && (
          <div className="flex items-center justify-between gap-4 border-t border-border pt-4">
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">Grading workflow</p>
              <p className="text-sm text-muted-foreground">
                Manual-review questions need teacher scores. Auto-scored questions are shown as reference and may only be overridden where the grading mode allows it.
              </p>
            </div>
            <Button type="button" onClick={() => void handleSaveScores()} disabled={isSavingScores}>
              {isSavingScores && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Grades
            </Button>
          </div>
        )}
      </section>

      <section className="rounded-sm border border-border bg-card p-6 space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Question Review</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Review rubric coverage, student responses, and the score state for each question.
            </p>
          </div>
        </div>

        {answerRows.length === 0 ? (
          <p className="text-sm text-muted-foreground">No answers found on this submission.</p>
        ) : (
          <div className="space-y-4">
            {answerRows.map(({ answer, question, index, manualReview, rubricMeta, canEdit, gradingLabel }) => {
              const isExpanded = expandedRubricQuestionIds.has(answer.questionId);
              const scoreLabel =
                gradingMode === 'AUTO'
                  ? 'Override Score'
                  : manualReview
                    ? 'Manual Score'
                    : 'Auto Score';

              return (
                <article
                  key={`${answer.questionId}-${index}`}
                  className={cn(
                    'rounded-sm border border-border bg-muted/10 p-5 space-y-4',
                    manualReview && 'border-amber-300/60 bg-amber-50/40 dark:bg-amber-900/10',
                  )}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <p className="text-sm font-semibold text-foreground">
                        Q{index + 1}. {question?.prompt || `Question #${answer.questionId}`}
                      </p>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="inline-flex items-center rounded-full border border-border bg-card px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                          {question ? formatQuestionKind(question.type) : answer.type}
                        </span>
                        <StatusBadge
                          status={
                            manualReview
                              ? 'SNAPSHOT'
                              : answer.score != null
                                ? 'ACTIVE'
                                : 'DRAFT'
                          }
                          label={gradingLabel}
                          className="text-[10px]"
                        />
                        <span className="text-xs text-muted-foreground">
                          Max {formatScore(question?.maxPoints ?? null)} pts
                        </span>
                      </div>
                    </div>
                    {rubricMeta.rubric && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => toggleRubric(answer.questionId)}
                        className="shrink-0"
                      >
                        {isExpanded ? (
                          <ChevronDown className="mr-1 h-4 w-4" />
                        ) : (
                          <ChevronRight className="mr-1 h-4 w-4" />
                        )}
                        {isExpanded ? 'Hide Rubric' : 'Show Rubric'}
                      </Button>
                    )}
                  </div>

                  <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
                    <div className="space-y-4">
                      <div className="space-y-1">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Student Response</p>
                        <div className="rounded-sm border border-border bg-card p-3 text-sm text-foreground">
                          {renderAnswer(question, answer)}
                        </div>
                      </div>

                      {rubricMeta.rubric && isExpanded && (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <p className="text-sm font-medium text-foreground">{rubricMeta.rubric.title}</p>
                              <p className="text-xs text-muted-foreground">
                                Rubric source: {rubricMeta.source}
                              </p>
                            </div>
                          </div>
                          <RubricGridPreview
                            criteria={rubricMeta.rubric.criteria}
                            title={`Rubric Reference — ${rubricMeta.rubric.title}`}
                          />
                        </div>
                      )}
                    </div>

                    <div className="rounded-sm border border-border bg-card p-4 space-y-3">
                      <div>
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Rubric</p>
                        <p className="mt-1 text-sm text-foreground">
                          {rubricMeta.rubric?.title ?? 'No rubric attached'}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Source: {rubricMeta.source}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">{scoreLabel}</p>
                        {canEdit ? (
                          <Input
                            value={scoreInputs[answer.questionId] ?? ''}
                            onChange={(event) =>
                              setScoreInputs((prev) => ({
                                ...prev,
                                [answer.questionId]: event.target.value,
                              }))
                            }
                            className="mt-2 max-w-[140px]"
                            inputMode="decimal"
                            placeholder="0"
                          />
                        ) : (
                          <p className="mt-2 text-sm text-foreground">{formatScore(answer.score)}</p>
                        )}
                      </div>

                      {(manualReview || canOverride) && (
                        <div className="text-xs text-muted-foreground space-y-1">
                          {manualReview ? (
                            <p>This question requires teacher grading.</p>
                          ) : canOverride && gradingMode === 'AUTO' ? (
                            <p>This question was auto-scored. Any change here is an override.</p>
                          ) : canOverride ? (
                            <p>This question keeps its system score in hybrid mode.</p>
                          ) : null}
                        </div>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
