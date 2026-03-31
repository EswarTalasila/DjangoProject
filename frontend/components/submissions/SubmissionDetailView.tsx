'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  getSubmission,
  overrideSubmissionScore,
  type AnswerPayload,
  type SubmissionDTO,
} from '@/lib/submission-api';
import { getAssignment, getAssignmentTemplate, type Assignment } from '@/lib/assignment-api';
import type { Assessment, Question } from '@/lib/assessment-api';
import { toErrorMessage, formatDate, formatScore } from '@/lib/utils';

type Role = 'ADMIN' | 'TEACHER' | 'RESEARCHER' | 'STUDENT';

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
  return 'No response';
}

function defaultScoreInput(answer: AnswerPayload): string {
  if (answer.score == null) return '';
  if (Number.isInteger(answer.score)) return String(answer.score);
  return answer.score.toFixed(2).replace(/\.?0+$/, '');
}

export default function SubmissionDetailView({ submissionId, viewerRole }: SubmissionDetailViewProps) {
  const [submission, setSubmission] = useState<SubmissionDTO | null>(null);
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [assessmentTemplate, setAssessmentTemplate] = useState<Assessment | null>(null);
  const [scoreInputs, setScoreInputs] = useState<Record<number, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isSavingScores, setIsSavingScores] = useState(false);

  const canOverride = viewerRole === 'TEACHER' || viewerRole === 'ADMIN';

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const currentSubmission = await getSubmission(submissionId);
      const [assignmentRecord, template] = await Promise.all([
        getAssignment(currentSubmission.assignmentId),
        getAssignmentTemplate(currentSubmission.assignmentId),
      ]);
      setSubmission(currentSubmission);
      setAssignment(assignmentRecord);
      setAssessmentTemplate(template);

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

  const editableQuestionIds = useMemo(() => {
    if (!submission) return new Set<number>();
    if (gradingMode !== 'HYBRID') {
      return new Set(submission.answers.map((answer) => answer.questionId));
    }
    return new Set(
      submission.answers
        .filter((answer) => answer.type === 'SHORT_ANSWER')
        .map((answer) => answer.questionId),
    );
  }, [gradingMode, submission]);

  async function handleSaveScores() {
    if (!submission || !canOverride) return;

    const targetAnswers =
      gradingMode === 'HYBRID'
        ? submission.answers.filter((answer) => answer.type === 'SHORT_ANSWER')
        : submission.answers;

    if (targetAnswers.length === 0) {
      toast.error('No gradable answers found for score override.');
      return;
    }

    const payload: number[] = [];
    for (const answer of targetAnswers) {
      const input = scoreInputs[answer.questionId] ?? '';
      const parsed = input.trim() === '' ? (answer.score ?? 0) : Number(input);
      if (Number.isNaN(parsed) || parsed < 0) {
        toast.error('All score values must be valid non-negative numbers.');
        return;
      }
      payload.push(parsed);
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (loadError || !submission) {
    return (
      <div className="space-y-6 p-6 w-full">
        <Link
          href="/dashboard/submissions"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          Back to Submissions
        </Link>
        <p className="text-sm text-destructive">{loadError ?? 'Submission not found.'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 w-full">
      <Link
        href="/dashboard/submissions"
        className="text-sm text-muted-foreground hover:text-foreground"
      >
        Back to Submissions
      </Link>

      <section className="rounded-sm border border-border bg-card p-6 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Submission #{submission.id}
            </h1>
            <p className="text-muted-foreground mt-1">
              {assignment?.title || `Assignment #${submission.assignmentId}`}
            </p>
          </div>
          <span className="bg-muted text-muted-foreground px-2 py-0.5 rounded text-xs font-medium">
            {submission.status}
          </span>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Student</p>
            <p className="text-sm text-foreground">
              {submission.studentId != null ? `#${submission.studentId}` : '-'}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Submitted</p>
            <p className="text-sm text-foreground">{formatDate(submission.submittedAt)}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Score</p>
            <p className="text-sm text-foreground">
              {formatScore(submission.score)} / {formatScore(totalPoints)}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Grading Mode</p>
            <p className="text-sm text-foreground">{gradingMode}</p>
          </div>
        </div>

        {canOverride && (
          <div className="flex items-center justify-between gap-3 border-t border-border pt-4">
            <p className="text-sm text-muted-foreground">
              {gradingMode === 'HYBRID'
                ? 'Hybrid mode: only short-answer question scores are editable.'
                : 'Override scores and save to mark this submission graded.'}
            </p>
            <Button type="button" onClick={() => void handleSaveScores()} disabled={isSavingScores}>
              {isSavingScores && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Scores
            </Button>
          </div>
        )}
      </section>

      <section className="rounded-sm border border-border bg-card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Answers</h2>
        {submission.answers.length === 0 ? (
          <p className="text-sm text-muted-foreground">No answers found on this submission.</p>
        ) : (
          <div className="space-y-4">
            {submission.answers.map((answer, index) => {
              const question = questionsById.get(answer.questionId);
              const isEditable = canOverride && editableQuestionIds.has(answer.questionId);
              return (
                <div
                  key={`${answer.questionId}-${index}`}
                  className="rounded-sm border border-border bg-muted/10 p-4 space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-foreground">
                        Q{index + 1}. {question?.prompt || `Question #${answer.questionId}`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {question ? formatQuestionKind(question.type) : answer.type} • Max{' '}
                        {formatScore(question?.maxPoints ?? null)} pts
                      </p>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Student Response</p>
                    <p className="text-sm text-foreground">{renderAnswer(question, answer)}</p>
                  </div>

                  <div className="flex items-center gap-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground w-24">Score</p>
                    {isEditable ? (
                      <Input
                        value={scoreInputs[answer.questionId] ?? ''}
                        onChange={(event) =>
                          setScoreInputs((prev) => ({
                            ...prev,
                            [answer.questionId]: event.target.value,
                          }))
                        }
                        className="max-w-[120px]"
                        inputMode="decimal"
                        placeholder="0"
                      />
                    ) : (
                      <p className="text-sm text-muted-foreground">{formatScore(answer.score)}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
