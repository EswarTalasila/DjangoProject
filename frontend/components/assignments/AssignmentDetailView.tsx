'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import {
  getAssignmentContent,
  archiveAssignment,
  type AssignmentContent,
  getAssignment,
  restoreAssignment,
  updateAssignment,
  type Assignment,
  type AssignmentQuestion as Question,
  type AssignmentUpdateInput,
} from '@/lib/assignment-api';
import { listCourses } from '@/lib/course-api';
import {
  getStudentSubmission,
  saveDraft,
  submitFinal,
  type AnswerPayload,
  type SubmissionDTO,
  type SubmissionStatus,
} from '@/lib/submission-api';
import { cn, toErrorMessage } from '@/lib/utils';
import AssignmentComposerPanel from './AssignmentComposerPanel';
import AssignmentMetadataPanel from './AssignmentMetadataPanel';
import StudentSubmissionForm from './StudentSubmissionForm';

type AssignmentDetailViewProps = {
  assignmentId: number;
  canMutate: boolean;
  viewerRole: 'TEACHER' | 'RESEARCHER' | 'ADMIN' | 'STUDENT';
  viewerId: number;
  mode?: 'detail' | 'edit';
};

type PreviewMode = 'teacher' | 'student';
type MoodSelection = {
  quadrant: string;
  moodName: string;
  row: number;
  col: number;
};

type StudentAttemptAnswer = {
  selectedChoiceIndexes: number[];
  textResponse: string;
  numericResponse: number | null;
  moodSelection: MoodSelection | null;
};
type StudentFlowStage = 'attempt' | 'submitted';

function toLocalInputValue(value: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toIsoOrNull(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function defaultStudentAnswer(question: Question): StudentAttemptAnswer {
  return {
    selectedChoiceIndexes: [],
    textResponse: '',
    numericResponse: null,
    moodSelection: null,
  };
}

function isQuestionAnswered(question: Question, answer: StudentAttemptAnswer): boolean {
  if (question.type === 'MULTIPLE_CHOICE') {
    return answer.selectedChoiceIndexes.length > 0;
  }
  if (question.type === 'SHORT_ANSWER') {
    return answer.textResponse.trim().length > 0;
  }
  if (question.type === 'NUMBER_SCALE') {
    return answer.numericResponse !== null;
  }
  if (question.type === 'MOOD_METER') {
    return answer.moodSelection !== null;
  }
  return false;
}

function estimateAutoPoints(question: Question, answer: StudentAttemptAnswer): number | null {
  if (question.type === 'MULTIPLE_CHOICE') {
    const choices = question.data?.choices ?? [];
    return answer.selectedChoiceIndexes.reduce((sum, idx) => sum + (choices[idx]?.score ?? 0), 0);
  }
  if (question.type === 'NUMBER_SCALE') {
    const target = question.data?.target;
    if (target == null || answer.numericResponse == null) return null;
    return answer.numericResponse === target ? question.maxPoints : 0;
  }
  return null;
}

function toAnswerPayloads(
  questions: Question[],
  answers: Record<number, StudentAttemptAnswer>,
): AnswerPayload[] {
  return questions.map((q) => {
    const answer = answers[q.questionId] ?? defaultStudentAnswer(q);
    if (q.type === 'MULTIPLE_CHOICE') {
      return { questionId: q.questionId, type: 'MULTIPLE_CHOICE', data: { selected: answer.selectedChoiceIndexes } };
    }
    if (q.type === 'SHORT_ANSWER') {
      return { questionId: q.questionId, type: 'SHORT_ANSWER', data: { text: answer.textResponse } };
    }
    if (q.type === 'MOOD_METER') {
      return {
        questionId: q.questionId,
        type: 'MOOD_METER',
        data: {
          quadrant: answer.moodSelection?.quadrant ?? '',
          moodName: answer.moodSelection?.moodName ?? '',
          row: answer.moodSelection?.row ?? 0,
          col: answer.moodSelection?.col ?? 0,
        },
      };
    }
    return { questionId: q.questionId, type: 'NUMBER_SCALE', data: { val: answer.numericResponse } };
  });
}

function hydrateStudentAnswers(
  questions: Question[],
  submission: SubmissionDTO,
): Record<number, StudentAttemptAnswer> {
  const result: Record<number, StudentAttemptAnswer> = {};
  for (const q of questions) {
    const backendAnswer = submission.answers.find((a) => a.questionId === q.questionId);
    if (backendAnswer) {
      result[q.questionId] = {
        selectedChoiceIndexes: backendAnswer.data?.selected ?? [],
        textResponse: backendAnswer.data?.text ?? '',
        numericResponse: backendAnswer.data?.val ?? null,
        moodSelection: backendAnswer.data?.quadrant
          ? {
              quadrant: backendAnswer.data.quadrant as string,
              moodName: backendAnswer.data.moodName as string,
              row: backendAnswer.data.row as number,
              col: backendAnswer.data.col as number,
            }
          : null,
      };
    } else {
      result[q.questionId] = defaultStudentAnswer(q);
    }
  }
  return result;
}

export default function AssignmentDetailView({
  assignmentId,
  canMutate,
  viewerRole,
  viewerId,
  mode = 'detail',
}: AssignmentDetailViewProps) {
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [assignmentContent, setAssignmentContent] = useState<AssignmentContent | null>(null);
  const [courseName, setCourseName] = useState<string>('');
  const [titleInput, setTitleInput] = useState('');
  const [openAtInput, setOpenAtInput] = useState('');
  const [dueAtInput, setDueAtInput] = useState('');
  const [previewMode, setPreviewMode] = useState<PreviewMode>(
    viewerRole === 'STUDENT' ? 'student' : 'teacher',
  );
  const [studentFlowStage, setStudentFlowStage] = useState<StudentFlowStage>('attempt');
  const [studentSubmittedAt, setStudentSubmittedAt] = useState<Date | null>(null);
  const [studentQuestionIndex, setStudentQuestionIndex] = useState(0);
  const [studentAnswers, setStudentAnswers] = useState<Record<number, StudentAttemptAnswer>>(
    {},
  );
  const [submission, setSubmission] = useState<SubmissionDTO | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [draftStatus, setDraftStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const draftTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isDirtyRef = useRef(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const item = await getAssignment(assignmentId);
      const [content, courses] = await Promise.all([
        getAssignmentContent(item.id),
        listCourses().catch(() => []),
      ]);

      setAssignment(item);
      setAssignmentContent(content);
      setTitleInput(item.title || content?.assignmentTemplateTitle || 'Untitled Assignment');
      setOpenAtInput(toLocalInputValue(item.openAt));
      setDueAtInput(toLocalInputValue(item.dueAt));

      const cName = courses.find((c) => c.id === item.courseId)?.name;
      setCourseName(cName ?? (item.courseId ? `Course #${item.courseId}` : '-'));

      if (viewerRole === 'STUDENT' && content) {
        try {
          const sub = await getStudentSubmission(viewerId, assignmentId);
          setSubmission(sub);
          setStudentAnswers(hydrateStudentAnswers(content.questions, sub));
          if (sub.status === 'SUBMITTED' || sub.status === 'GRADED') {
            setStudentFlowStage('submitted');
            setStudentSubmittedAt(sub.submittedAt ? new Date(sub.submittedAt) : null);
          }
        } catch (error: unknown) {
          const axErr = error as { response?: { data?: { detail?: string }; status?: number } };
          const statusCode = axErr.response?.status;
          const detail = axErr.response?.data?.detail;
          const missingSubmission =
            statusCode === 404 && (detail?.toLowerCase().includes('submission') ?? true);
          if (!missingSubmission) {
            throw error;
          }
          // No existing submission — student starts fresh
        }
      }
    } catch (error: unknown) {
      setLoadError(toErrorMessage(error, 'Failed to load assignment.'));
    } finally {
      setIsLoading(false);
    }
  }, [assignmentId, viewerRole, viewerId]);

  useEffect(() => {
    setIsLoading(true);
    void load();
  }, [load]);

  const canEditAssignment = useMemo(() => {
    return canMutate && assignment?.status === 'ACTIVE';
  }, [assignment?.status, canMutate]);

  const totalPoints = useMemo(() => {
    if (!assignmentContent) return 0;
    return assignmentContent.questions.reduce((sum, q) => sum + q.maxPoints, 0);
  }, [assignmentContent]);

  const flatQuestions = useMemo(() => {
    return assignmentContent?.questions ?? [];
  }, [assignmentContent]);

  const clampedStudentQuestionIndex = useMemo(() => {
    if (flatQuestions.length === 0) return 0;
    return Math.max(0, Math.min(studentQuestionIndex, flatQuestions.length - 1));
  }, [flatQuestions.length, studentQuestionIndex]);

  const activeStudentQuestion = flatQuestions[clampedStudentQuestionIndex] ?? null;
  const activeStudentAnswer = useMemo(() => {
    if (!activeStudentQuestion) return null;
    return studentAnswers[activeStudentQuestion.questionId] ?? defaultStudentAnswer(activeStudentQuestion);
  }, [activeStudentQuestion, studentAnswers]);

  const answeredQuestionIds = useMemo(() => {
    const answered = new Set<number>();
    for (const question of flatQuestions) {
      const answer = studentAnswers[question.questionId] ?? defaultStudentAnswer(question);
      if (isQuestionAnswered(question, answer)) {
        answered.add(question.questionId);
      }
    }
    return answered;
  }, [flatQuestions, studentAnswers]);

  const answeredCount = answeredQuestionIds.size;
  const autoPointsEarned = useMemo(() => {
    return flatQuestions.reduce((sum, question) => {
      const answer = studentAnswers[question.questionId] ?? defaultStudentAnswer(question);
      const points = estimateAutoPoints(question, answer);
      return sum + (points ?? 0);
    }, 0);
  }, [flatQuestions, studentAnswers]);

  useEffect(() => {
    setStudentQuestionIndex(0);
    // Only reset flow stage if not loaded from backend
    if (!submission || (submission.status !== 'SUBMITTED' && submission.status !== 'GRADED')) {
      setStudentFlowStage('attempt');
      setStudentSubmittedAt(null);
    }
  }, [assignmentContent?.assignmentId, previewMode, submission]);

  useEffect(() => {
    if (flatQuestions.length === 0) {
      setStudentAnswers({});
      return;
    }
    // Preserve existing answers (hydrated from backend or user-entered)
    setStudentAnswers((prev) => {
      if (Object.keys(prev).length > 0) return prev;
      const next: Record<number, StudentAttemptAnswer> = {};
      for (const question of flatQuestions) {
        next[question.questionId] = defaultStudentAnswer(question);
      }
      return next;
    });
  }, [flatQuestions]);

  const submissionLocked = submission?.status === 'SUBMITTED' || submission?.status === 'GRADED';
  const submissionStatus: SubmissionStatus = submission?.status ?? 'NOT_STARTED';

  const assignmentArchived = assignment?.status === 'ARCHIVED';
  const editHref = canEditAssignment ? `/dashboard/assignments/${assignmentId}/edit` : null;
  const assignmentNotOpen = useMemo(() => {
    if (!assignment?.openAt) return false;
    return new Date(assignment.openAt) > new Date();
  }, [assignment?.openAt]);
  const studentBlocked = assignmentArchived || assignmentNotOpen;

  function updateStudentAnswer(question: Question, updater: (curr: StudentAttemptAnswer) => StudentAttemptAnswer) {
    if (submissionLocked || studentBlocked) return;
    isDirtyRef.current = true;
    setStudentAnswers((prev) => {
      const current = prev[question.questionId] ?? defaultStudentAnswer(question);
      return {
        ...prev,
        [question.questionId]: updater(current),
      };
    });
  }

  // Debounced draft save — fires 1s after last answer change (student only)
  useEffect(() => {
    if (viewerRole !== 'STUDENT' || submissionLocked || studentBlocked || flatQuestions.length === 0) return;
    // Skip if still loading initial data or user hasn't interacted yet
    if (isLoading || !isDirtyRef.current) return;

    if (draftTimerRef.current) clearTimeout(draftTimerRef.current);

    draftTimerRef.current = setTimeout(() => {
      draftTimerRef.current = null;
      const payloads = toAnswerPayloads(flatQuestions, studentAnswers);
      setDraftStatus('saving');
      saveDraft(viewerId, assignmentId, payloads)
        .then((saved) => {
          setSubmission(saved);
          setDraftStatus('saved');
          setTimeout(() => setDraftStatus('idle'), 2000);
        })
        .catch(() => {
          setDraftStatus('error');
        });
    }, 1000);

    return () => {
      if (draftTimerRef.current) clearTimeout(draftTimerRef.current);
    };
  }, [assignmentId, flatQuestions, isLoading, studentAnswers, studentBlocked, submissionLocked, viewerId, viewerRole]);

  // Ensure no delayed draft save can fire once submission is locked/submitting.
  useEffect(() => {
    if (!submissionLocked && !isSubmitting) return;
    if (draftTimerRef.current) {
      clearTimeout(draftTimerRef.current);
      draftTimerRef.current = null;
    }
  }, [isSubmitting, submissionLocked]);

  async function handleRealSubmit() {
    if (submissionLocked || studentBlocked || flatQuestions.length === 0) return;
    if (draftTimerRef.current) {
      clearTimeout(draftTimerRef.current);
      draftTimerRef.current = null;
    }
    setIsSubmitting(true);
    try {
      const payloads = toAnswerPayloads(flatQuestions, studentAnswers);
      const result = await submitFinal(assignmentId, viewerId, payloads);
      setSubmission(result);
      setStudentFlowStage('submitted');
      setStudentSubmittedAt(result.submittedAt ? new Date(result.submittedAt) : new Date());
      toast.success('Submission sent successfully.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to submit. Please try again.'));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleUpdateAssignment() {
    if (!assignment) return;

    const trimmedTitle = titleInput.trim();
    if (!trimmedTitle) {
      toast.error('Assignment title cannot be empty.');
      return;
    }

    const openIso = toIsoOrNull(openAtInput);
    const dueIso = toIsoOrNull(dueAtInput);

    if (!openIso) {
      toast.error('Please provide a valid open date/time.');
      return;
    }
    if (dueIso && openIso >= dueIso) {
      toast.error('Open time must be before due time.');
      return;
    }

    const payload: AssignmentUpdateInput = {
      title: trimmedTitle,
      openAt: openIso,
      dueAt: dueIso,
    };

    setIsUpdating(true);
    try {
      const updated = await updateAssignment(assignment.id, payload);
      setAssignment(updated);
      setTitleInput(updated.title || trimmedTitle);
      setOpenAtInput(toLocalInputValue(updated.openAt));
      setDueAtInput(toLocalInputValue(updated.dueAt));
      toast.success('Assignment updated.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to update assignment.'));
    } finally {
      setIsUpdating(false);
    }
  }

  async function handleArchive() {
    if (!assignment) return;

    setIsArchiving(true);
    try {
      const updated = await archiveAssignment(assignment.id);
      setAssignment(updated);
      toast.success('Assignment archived.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to archive assignment.'));
    } finally {
      setIsArchiving(false);
    }
  }

  async function handleRestore() {
    if (!assignment) return;

    setIsRestoring(true);
    try {
      const restored = await restoreAssignment(assignment.id);
      setAssignment(restored);
      toast.success('Assignment restored.');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to restore assignment.'));
    } finally {
      setIsRestoring(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (loadError || !assignment) {
    return (
      <div className="space-y-6 p-6 max-w-5xl mx-auto">
        <Link
          href="/dashboard/assignments"
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Assignments
        </Link>
        <p className="text-sm text-destructive">{loadError ?? 'Assignment not found.'}</p>
      </div>
    );
  }

  return (
    <div className={cn('w-full', mode === 'edit' ? 'p-0' : 'space-y-6 p-6')}>
      <div className={cn(mode === 'edit' ? 'px-6 pt-6' : '')}>
        <Link
          href={mode === 'edit' ? `/dashboard/assignments/${assignmentId}` : '/dashboard/assignments'}
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          {mode === 'edit' ? 'Back to Assignment' : 'Back to Assignments'}
        </Link>
      </div>

      {mode !== 'edit' ? (
        <AssignmentMetadataPanel
          assignment={assignment}
          assignmentTemplate={assignmentContent}
          courseName={courseName}
          totalPoints={totalPoints}
          canMutate={canMutate}
          canEditAssignment={canEditAssignment}
          titleInput={titleInput}
          onTitleInputChange={setTitleInput}
          openAtInput={openAtInput}
          onOpenAtInputChange={setOpenAtInput}
          dueAtInput={dueAtInput}
          onDueAtInputChange={setDueAtInput}
          previewMode={previewMode}
          onPreviewModeChange={setPreviewMode}
          showPreviewModeToggle
          editHref={editHref}
          isUpdating={isUpdating}
          isArchiving={isArchiving}
          isRestoring={isRestoring}
          onUpdate={() => void handleUpdateAssignment()}
          onArchive={() => void handleArchive()}
          onRestore={() => void handleRestore()}
        />
      ) : null}

      <div className={cn(mode === 'edit' ? 'px-4 pb-6 pt-4 lg:px-6' : 'rounded-sm border border-border bg-card p-4 space-y-4 lg:p-6 lg:min-h-[760px]')}>
        {mode !== 'edit' ? (
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Assignment Content</h2>
          <span className="text-xs uppercase tracking-wide text-muted-foreground">
            {previewMode === 'teacher' ? 'Teacher view' : 'Student preview'}
          </span>
        </div>
        ) : null}

        {!assignmentContent || (assignmentContent.questions.length === 0 && assignmentContent.submissionMode === 'DIGITAL') ? (
          <p className="text-sm text-muted-foreground">No questions in this assignment template.</p>
        ) : mode === 'edit' ? (
          <AssignmentComposerPanel
            assignmentId={assignment.id}
            content={assignmentContent}
            canCompose={canEditAssignment}
            onContentChange={setAssignmentContent}
          />
        ) : previewMode === 'student' ? (
          <StudentSubmissionForm
            viewerRole={viewerRole}
            assignmentArchived={assignmentArchived}
            assignmentNotOpen={assignmentNotOpen}
            openAt={assignment?.openAt ?? null}
            submissionMode={assignmentContent?.submissionMode ?? 'DIGITAL'}
            flatQuestions={flatQuestions}
            studentAnswers={studentAnswers}
            studentFlowStage={studentFlowStage}
            studentSubmittedAt={studentSubmittedAt}
            clampedStudentQuestionIndex={clampedStudentQuestionIndex}
            activeStudentQuestion={activeStudentQuestion}
            activeStudentAnswer={activeStudentAnswer}
            answeredQuestionIds={answeredQuestionIds}
            answeredCount={answeredCount}
            autoPointsEarned={autoPointsEarned}
            totalPoints={totalPoints}
            submission={submission}
            submissionLocked={submissionLocked}
            submissionStatus={submissionStatus}
            studentBlocked={studentBlocked}
            isSubmitting={isSubmitting}
            draftStatus={draftStatus}
            onStudentQuestionIndexChange={setStudentQuestionIndex}
            onUpdateStudentAnswer={updateStudentAnswer}
            onSubmit={() => void handleRealSubmit()}
            onSetFlowStage={setStudentFlowStage}
            onSetSubmittedAt={setStudentSubmittedAt}
          />
        ) : (
          <section className="space-y-6">
            <div className="rounded-2xl border border-border/70 bg-background p-5">
              <h3 className="text-base font-semibold text-foreground">Assignment questions</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Shared questions stay fixed. Any teacher-added questions appear here too. Use Edit assignment if you want to add or adjust local questions or rubric items for this class.
              </p>
            </div>

            <div className="space-y-3">
              {assignmentContent.questions.map((question, index) => (
                <div
                  key={question.id}
                  className="rounded-2xl border border-border/70 bg-background px-4 py-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                        Question {index + 1}
                      </p>
                      <p className="mt-1 text-base font-medium text-foreground">{question.prompt}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">
                        {question.type.replaceAll('_', ' ')}
                      </p>
                      <p className="mt-1 text-sm text-muted-foreground">{question.maxPoints} pts</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
