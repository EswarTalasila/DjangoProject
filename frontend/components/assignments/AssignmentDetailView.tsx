'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Loader2 } from 'lucide-react';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  archiveAssignment,
  deleteAssignment,
  getAssignment,
  updateAssignment,
  type Assignment,
  type AssignmentUpdateInput,
} from '@/lib/assignment-api';
import { getAssessment, type Assessment, type Question } from '@/lib/assessment-api';
import { listCourses } from '@/lib/course-api';

type ApiError = { response?: { data?: { detail?: string }; status?: number } };

type AssignmentDetailViewProps = {
  assignmentId: number;
  canMutate: boolean;
  viewerRole: 'TEACHER' | 'RESEARCHER' | 'ADMIN' | 'STUDENT';
};

type PreviewMode = 'teacher' | 'student';
type StudentAttemptAnswer = {
  selectedChoiceIndexes: number[];
  textResponse: string;
  numericResponse: number | null;
};

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

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

function formatDate(value: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
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
  if (question.type === 'NUMBER_SCALE') {
    const min = question.data?.min ?? question.min ?? 1;
    return {
      selectedChoiceIndexes: [],
      textResponse: '',
      numericResponse: min,
    };
  }
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

function StudentQuestionPreview({
  question,
  answer,
  onSelectChoice,
  onTextChange,
  onNumberChange,
}: {
  question: Question;
  answer: StudentAttemptAnswer;
  onSelectChoice: (choiceIndex: number, checked: boolean) => void;
  onTextChange: (nextValue: string) => void;
  onNumberChange: (nextValue: number) => void;
}) {
  const data = question.data;

  if (question.type === 'MULTIPLE_CHOICE') {
    const isSelectAll = Boolean(data?.selectAll);
    return (
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground">
          {isSelectAll ? 'Select all that apply.' : 'Select one option.'}
        </p>
        {(data?.choices ?? []).map((choice, idx) => (
          <label
            key={`${choice.prompt}-${idx}`}
            className="flex items-center gap-2 rounded border border-border bg-muted/20 px-3 py-2 text-sm"
          >
            <input
              type={isSelectAll ? 'checkbox' : 'radio'}
              name={`student-preview-q-${question.questionId}`}
              checked={answer.selectedChoiceIndexes.includes(idx)}
              onChange={(event) => onSelectChoice(idx, event.target.checked)}
            />
            <span>{choice.prompt || '(empty choice)'}</span>
          </label>
        ))}
      </div>
    );
  }

  if (question.type === 'SHORT_ANSWER') {
    return (
      <textarea
        className="w-full min-h-24 rounded border border-border bg-muted/20 px-3 py-2 text-sm text-muted-foreground"
        placeholder="Student response appears here..."
        value={answer.textResponse}
        onChange={(event) => onTextChange(event.target.value)}
      />
    );
  }

  if (question.type === 'NUMBER_SCALE') {
    const min = data?.min ?? question.min ?? 1;
    const max = data?.max ?? question.max ?? 10;
    return (
      <div className="space-y-2">
        <input
          type="range"
          min={min}
          max={max}
          value={answer.numericResponse ?? min}
          onChange={(event) => onNumberChange(Number(event.target.value))}
          className="w-full"
        />
        <p className="text-xs text-muted-foreground">
          Student selects a value between {min} and {max}. Current: {answer.numericResponse ?? min}
        </p>
      </div>
    );
  }

  return <p className="text-sm text-muted-foreground">Preview unavailable for this question type.</p>;
}

export default function AssignmentDetailView({
  assignmentId,
  canMutate,
  viewerRole,
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
  const [studentQuestionIndex, setStudentQuestionIndex] = useState(0);
  const [studentAnswers, setStudentAnswers] = useState<Record<number, StudentAttemptAnswer>>(
    {},
  );
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
        getAssessment(item.assessmentId).catch(() => null),
        listCourses().catch(() => []),
      ]);

      setAssignment(item);
      setAssessmentTemplate(template);
      setTitleInput(item.title || template?.title || `Assignment #${item.id}`);
      setOpenAtInput(toLocalInputValue(item.openAt));
      setDueAtInput(toLocalInputValue(item.dueAt));

      const cName = courses.find((c) => c.id === item.courseId)?.name;
      setCourseName(cName ?? (item.courseId ? `Course #${item.courseId}` : '-'));
    } catch {
      setLoadError('Failed to load assignment.');
    } finally {
      setIsLoading(false);
    }
  }, [assignmentId]);

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

  useEffect(() => {
    setStudentQuestionIndex(0);
  }, [assessmentTemplate?.id, previewMode]);

  useEffect(() => {
    if (flatQuestions.length === 0) {
      setStudentAnswers({});
      return;
    }
    setStudentAnswers((prev) => {
      const next: Record<number, StudentAttemptAnswer> = {};
      for (const question of flatQuestions) {
        next[question.questionId] = prev[question.questionId] ?? defaultStudentAnswer(question);
      }
      return next;
    });
  }, [flatQuestions]);

  function updateStudentAnswer(question: Question, updater: (curr: StudentAttemptAnswer) => StudentAttemptAnswer) {
    setStudentAnswers((prev) => {
      const current = prev[question.questionId] ?? defaultStudentAnswer(question);
      return {
        ...prev,
        [question.questionId]: updater(current),
      };
    });
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
      toast.error(extractDetail(error, 'Failed to update assignment.'));
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
      toast.error(extractDetail(error, 'Failed to archive assignment.'));
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
      toast.error(extractDetail(error, 'Failed to delete assignment.'));
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
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      <Link
        href="/dashboard/assignments"
        className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Assignments
      </Link>

      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            {assignment.title || `Assignment #${assignment.id}`}
          </h1>
          <p className="text-muted-foreground mt-1">
            {assessmentTemplate?.title ?? `Assessment #${assignment.assessmentId}`} • {courseName}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {canMutate && (
            <div className="rounded border border-border p-1 flex items-center gap-1 bg-card">
              <Button
                type="button"
                size="sm"
                variant={previewMode === 'teacher' ? 'default' : 'ghost'}
                  onClick={() => setPreviewMode('teacher')}
              >
                Teacher View
              </Button>
              <Button
                type="button"
                size="sm"
                variant={previewMode === 'student' ? 'default' : 'ghost'}
                  onClick={() => setPreviewMode('student')}
              >
                Student View
              </Button>
            </div>
          )}
          <span className="bg-muted text-muted-foreground px-2 py-0.5 rounded text-xs font-medium">
            {assignment.status}
          </span>
        </div>
      </div>

      <div className="rounded-sm border border-border bg-card p-6 space-y-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Template</p>
            <p className="text-sm text-foreground">{assessmentTemplate?.title ?? '-'}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Course</p>
            <p className="text-sm text-foreground">{courseName}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Questions</p>
            <p className="text-sm text-foreground">{assessmentTemplate?.questions.length ?? 0}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Total Points</p>
            <p className="text-sm text-foreground">{formatPoints(totalPoints)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Open At</p>
            <p className="text-sm text-foreground">{formatDate(assignment.openAt)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Due At</p>
            <p className="text-sm text-foreground">{formatDate(assignment.dueAt)}</p>
          </div>
        </div>
      </div>

      {canMutate && (
        <div className="rounded-sm border border-border bg-card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-foreground">Manage Assignment</h2>

          <div className="space-y-2">
            <Label htmlFor="assignment-title">Assignment Title</Label>
            <Input
              id="assignment-title"
              value={titleInput}
              onChange={(event) => setTitleInput(event.target.value)}
              disabled={!canEditAssignment || isUpdating}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="open-at">Open At</Label>
              <Input
                id="open-at"
                type="datetime-local"
                value={openAtInput}
                onChange={(event) => setOpenAtInput(event.target.value)}
                disabled={!canEditAssignment || isUpdating}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="due-at">Due At</Label>
              <Input
                id="due-at"
                type="datetime-local"
                value={dueAtInput}
                onChange={(event) => setDueAtInput(event.target.value)}
                disabled={!canEditAssignment || isUpdating}
              />
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <Button onClick={() => void handleUpdateAssignment()} disabled={!canEditAssignment || isUpdating}>
              {isUpdating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Changes
            </Button>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" disabled={assignment.status === 'ARCHIVED' || isArchiving}>
                  {isArchiving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Archive
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Archive Assignment</AlertDialogTitle>
                  <AlertDialogDescription>
                    Archiving hides this assignment from student active lists. This can’t be undone yet.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={isArchiving}>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={(event) => {
                      event.preventDefault();
                      void handleArchive();
                    }}
                    disabled={isArchiving}
                  >
                    Confirm Archive
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" disabled={isDeleting}>
                  {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Delete
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete Assignment</AlertDialogTitle>
                  <AlertDialogDescription>
                    Delete is blocked if submissions progressed beyond NOT_STARTED.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    variant="destructive"
                    onClick={(event) => {
                      event.preventDefault();
                      void handleDelete();
                    }}
                    disabled={isDeleting}
                  >
                    Confirm Delete
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      )}

      <div className="rounded-sm border border-border bg-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Assignment Content</h2>
          <span className="text-xs uppercase tracking-wide text-muted-foreground">
            {previewMode === 'teacher' ? 'Teacher template view' : 'Student preview'}
          </span>
        </div>

        {!assessmentTemplate || assessmentTemplate.questions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No questions in this assignment template.</p>
        ) : previewMode === 'student' ? (
          <div className="rounded-sm border border-border bg-card overflow-hidden">
            <div className="border-b border-border px-5 py-3 flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-foreground">
                  Student Attempt Preview
                </p>
                <p className="text-xs text-muted-foreground">
                  Question {clampedStudentQuestionIndex + 1} of {flatQuestions.length}
                </p>
              </div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Page {clampedStudentQuestionIndex + 1}/{flatQuestions.length}
              </p>
            </div>

            <div className="grid min-h-[620px] lg:grid-cols-[minmax(0,1fr)_280px]">
              <section className="min-h-0 flex flex-col border-b lg:border-b-0 lg:border-r border-border">
                {activeStudentQuestion && (
                  <>
                    <div className="px-5 py-4 border-b border-border bg-muted/10">
                      <p className="text-sm font-semibold text-foreground">
                        Q{clampedStudentQuestionIndex + 1}. {activeStudentQuestion.prompt}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatQuestionKind(activeStudentQuestion.type)} •{' '}
                        {formatPoints(activeStudentQuestion.maxPoints)} pts
                      </p>
                    </div>

                    <div className="min-h-0 flex-1 overflow-y-auto p-5">
                      <div className="max-w-3xl">
                        {activeStudentAnswer && (
                          <StudentQuestionPreview
                            question={activeStudentQuestion}
                            answer={activeStudentAnswer}
                            onSelectChoice={(choiceIndex, checked) => {
                              updateStudentAnswer(activeStudentQuestion, (curr) => {
                                const isSelectAll = Boolean(activeStudentQuestion.data?.selectAll);
                                if (!isSelectAll) {
                                  return {
                                    ...curr,
                                    selectedChoiceIndexes: checked ? [choiceIndex] : [],
                                  };
                                }
                                const existing = new Set(curr.selectedChoiceIndexes);
                                if (checked) {
                                  existing.add(choiceIndex);
                                } else {
                                  existing.delete(choiceIndex);
                                }
                                return {
                                  ...curr,
                                  selectedChoiceIndexes: [...existing].sort((a, b) => a - b),
                                };
                              });
                            }}
                            onTextChange={(nextValue) => {
                              updateStudentAnswer(activeStudentQuestion, (curr) => ({
                                ...curr,
                                textResponse: nextValue,
                              }));
                            }}
                            onNumberChange={(nextValue) => {
                              updateStudentAnswer(activeStudentQuestion, (curr) => ({
                                ...curr,
                                numericResponse: nextValue,
                              }));
                            }}
                          />
                        )}
                      </div>
                    </div>

                    <div className="border-t border-border px-5 py-3 flex items-center justify-between gap-3 bg-card">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() =>
                          setStudentQuestionIndex((prev) => Math.max(0, prev - 1))
                        }
                        disabled={clampedStudentQuestionIndex === 0}
                      >
                        Previous
                      </Button>
                      <div className="flex items-center gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() =>
                            setStudentQuestionIndex((prev) =>
                              Math.min(flatQuestions.length - 1, prev + 1),
                            )
                          }
                          disabled={clampedStudentQuestionIndex >= flatQuestions.length - 1}
                        >
                          Next
                        </Button>
                        <Button
                          type="button"
                          disabled={clampedStudentQuestionIndex < flatQuestions.length - 1}
                        >
                          Submit (Preview)
                        </Button>
                      </div>
                    </div>
                  </>
                )}
              </section>

              <aside className="p-4 bg-muted/20 hidden lg:block">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                  Question Navigator
                </p>
                <div className="grid grid-cols-4 gap-2">
                  {flatQuestions.map((question, idx) => {
                    const isActive = idx === clampedStudentQuestionIndex;
                    const isAnswered = answeredQuestionIds.has(question.questionId);
                    return (
                      <Button
                        key={`student-preview-nav-${idx}`}
                        type="button"
                        size="sm"
                        variant={isActive ? 'default' : 'outline'}
                        className={`h-8 px-0 ${!isActive && isAnswered ? 'border-emerald-500/60 text-emerald-700 dark:text-emerald-300' : ''}`}
                        onClick={() => setStudentQuestionIndex(idx)}
                      >
                        Q{idx + 1}{isAnswered ? ' •' : ''}
                      </Button>
                    );
                  })}
                </div>
              </aside>
            </div>
          </div>
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
