'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import {
  archiveAssignment,
  deleteAssignment,
  getAssignment,
  getAssignmentTemplate,
  updateAssignment,
  type Assignment,
  type AssignmentUpdateInput,
} from '@/lib/assignment-api';
import type { Assessment, Question } from '@/lib/assessment-api';
import { listCourses } from '@/lib/course-api';
import {
  getStudentSubmission,
  saveDraft,
  submitFinal,
  type AnswerPayload,
  type SubmissionDTO,
  type SubmissionStatus,
} from '@/lib/submission-api';
import { toErrorMessage } from '@/lib/utils';
import AssignmentMetadataPanel from './AssignmentMetadataPanel';
import StudentSubmissionForm from './StudentSubmissionForm';

type AssignmentDetailViewProps = {
  assignmentId: number;
  canMutate: boolean;
  viewerRole: 'TEACHER' | 'RESEARCHER' | 'ADMIN' | 'STUDENT';
  viewerId: number;
};

type PreviewMode = 'teacher' | 'student';
type StudentAttemptAnswer = {
  selectedChoiceIndexes: number[];
  textResponse: string;
  numericResponse: number | null;
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

function formatPoints(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(2).replace(/\.?0+$/, '');
}

function defaultStudentAnswer(question: Question): StudentAttemptAnswer {
  return {
    selectedChoiceIndexes: [],
    textResponse: '',
    numericResponse: null,
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

function TeacherQuestionDetails({ question }: { question: Question }) {
  const data = question.data;

  if (question.type === 'MULTIPLE_CHOICE' && data?.choices?.length) {
    return (
      <div className="space-y-1">
        <p className="text-xs text-muted-foreground">
          {data.selectAll ? 'Select all that apply' : 'Single correct option'}
        </p>
        <ol className="list-decimal list-inside space-y-1">
          {data.choices.map((choice, idx) => (
            <li key={`${choice.prompt}-${idx}`} className="text-sm text-foreground">
              {choice.prompt || '(empty choice)'}{' '}
              <span className="text-muted-foreground">• {formatPoints(choice.score)} pts</span>
            </li>
          ))}
        </ol>
      </div>
    );
  }

  if (question.type === 'SHORT_ANSWER') {
    return (
      <div className="text-xs text-muted-foreground space-y-1">
        <p>Trim whitespace: {data?.trim === false ? 'Off' : 'On'}</p>
        <p>Case sensitive: {data?.caseSensitive ? 'On' : 'Off'}</p>
      </div>
    );
  }

  if (question.type === 'NUMBER_SCALE') {
    const min = data?.min ?? question.min;
    const max = data?.max ?? question.max;
    return (
      <p className="text-xs text-muted-foreground">
        Range: {min ?? '?'} to {max ?? '?'}
      </p>
    );
  }

  return null;
}

function toAnswerPayloads(
  questions: Question[],
  answers: Record<number, StudentAttemptAnswer>,
): AnswerPayload[] {
  return questions.map((q) => {
    const a = answers[q.questionId] ?? defaultStudentAnswer(q);
    if (q.type === 'MULTIPLE_CHOICE') {
      return { questionId: q.questionId, type: 'MULTIPLE_CHOICE', data: { selected: a.selectedChoiceIndexes } };
    }
    if (q.type === 'SHORT_ANSWER') {
      return { questionId: q.questionId, type: 'SHORT_ANSWER', data: { text: a.textResponse } };
    }
    return { questionId: q.questionId, type: 'NUMBER_SCALE', data: { val: a.numericResponse } };
  });
}

function hydateStudentAnswers(
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
}: AssignmentDetailViewProps) {
  const router = useRouter();

  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [assessmentTemplate, setAssessmentTemplate] = useState<Assessment | null>(null);
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
  const [isDeleting, setIsDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const item = await getAssignment(assignmentId);
      const [template, courses] = await Promise.all([
        getAssignmentTemplate(item.id),
        listCourses().catch(() => []),
      ]);

      setAssignment(item);
      setAssessmentTemplate(template);
      setTitleInput(item.title || template?.title || 'Untitled Assignment');
      setOpenAtInput(toLocalInputValue(item.openAt));
      setDueAtInput(toLocalInputValue(item.dueAt));

      const cName = courses.find((c) => c.id === item.courseId)?.name;
      setCourseName(cName ?? (item.courseId ? `Course #${item.courseId}` : '-'));

      if (viewerRole === 'STUDENT' && template) {
        try {
          const sub = await getStudentSubmission(viewerId, assignmentId);
          setSubmission(sub);
          setStudentAnswers(hydateStudentAnswers(template.questions, sub));
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

  const groupedQuestionBuckets = useMemo(() => {
    if (!assessmentTemplate) {
      return [] as Array<{
        key: string;
        title: string;
        questions: Question[];
      }>;
    }

    const byGroupId = new Map<number, Question[]>();
    const ungrouped: Question[] = [];

    for (const question of assessmentTemplate.questions) {
      if (question.groupId != null) {
        const arr = byGroupId.get(question.groupId) ?? [];
        arr.push(question);
        byGroupId.set(question.groupId, arr);
      } else {
        ungrouped.push(question);
      }
    }

    const buckets: Array<{ key: string; title: string; questions: Question[] }> = [];

    for (const group of [...assessmentTemplate.questionGroups].sort((a, b) => a.orderIndex - b.orderIndex)) {
      buckets.push({
        key: `group-${group.id}`,
        title: group.name,
        questions: byGroupId.get(group.id) ?? [],
      });
    }

    if (ungrouped.length > 0 || buckets.length === 0) {
      buckets.push({ key: 'ungrouped', title: 'Ungrouped', questions: ungrouped });
    }

    return buckets;
  }, [assessmentTemplate]);

  const totalPoints = useMemo(() => {
    if (!assessmentTemplate) return 0;
    return assessmentTemplate.questions.reduce((sum, q) => sum + q.maxPoints, 0);
  }, [assessmentTemplate]);

  const flatQuestions = useMemo(() => {
    return assessmentTemplate?.questions ?? [];
  }, [assessmentTemplate]);

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
  }, [assessmentTemplate?.id, previewMode, submission]);

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

  async function handleDelete() {
    if (!assignment) return;

    setIsDeleting(true);
    try {
      await deleteAssignment(assignment.id);
      toast.success('Assignment deleted.');
      router.push('/dashboard/assignments');
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to delete assignment.'));
    } finally {
      setIsDeleting(false);
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
    <div className="w-full space-y-6 p-6">
      <Link
        href="/dashboard/assignments"
        className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Assignments
      </Link>

      <AssignmentMetadataPanel
        assignment={assignment}
        assessmentTemplate={assessmentTemplate}
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
        isUpdating={isUpdating}
        isArchiving={isArchiving}
        isDeleting={isDeleting}
        onUpdate={() => void handleUpdateAssignment()}
        onArchive={() => void handleArchive()}
        onDelete={() => void handleDelete()}
      />

      <div className="rounded-sm border border-border bg-card p-6 space-y-4 min-h-[760px]">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Assignment Content</h2>
          <span className="text-xs uppercase tracking-wide text-muted-foreground">
            {previewMode === 'teacher' ? 'Teacher template view' : 'Student preview'}
          </span>
        </div>

        {!assessmentTemplate || assessmentTemplate.questions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No questions in this assignment template.</p>
        ) : previewMode === 'student' ? (
          <StudentSubmissionForm
            viewerRole={viewerRole}
            assignmentArchived={assignmentArchived}
            assignmentNotOpen={assignmentNotOpen}
            openAt={assignment?.openAt ?? null}
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
          <div className="space-y-4">
            {groupedQuestionBuckets.map((bucket) => (
              <div key={bucket.key} className="rounded-sm border border-border p-4 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
                    {bucket.title}
                  </h3>
                  <span className="text-xs text-muted-foreground">
                    {bucket.questions.length} question(s)
                  </span>
                </div>

                {bucket.questions.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No questions in this group.</p>
                ) : (
                  <div className="space-y-3">
                    {bucket.questions.map((question, index) => (
                      <div key={question.questionId} className="rounded-sm border border-border bg-muted/10 p-4 space-y-3">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-foreground">
                              Q{index + 1}. {question.prompt}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {formatQuestionKind(question.type)} • {formatPoints(question.maxPoints)} pts
                              {previewMode === 'teacher' ? ` • Grading: ${question.gradingStrategy}` : ''}
                            </p>
                          </div>
                        </div>

                        <TeacherQuestionDetails question={question} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
