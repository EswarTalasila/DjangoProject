'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Loader2, Pencil, Trash2 } from 'lucide-react';
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
  deleteAssessment,
  getAssessment,
  type Assessment,
  type Question,
} from '@/lib/assessment-api';

type ApiError = { response?: { data?: { detail?: string }; status?: number } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

type AssessmentDetailViewProps = {
  assessmentId: number;
  canManage: boolean;
};

export default function AssessmentDetailView({
  assessmentId,
  canManage,
}: AssessmentDetailViewProps) {
  const router = useRouter();

  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadAssessment = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await getAssessment(assessmentId);
      setAssessment(data);
    } catch {
      setLoadError('Failed to load assessment.');
    } finally {
      setIsLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => {
    setIsLoading(true);
    void loadAssessment();
  }, [loadAssessment]);

  async function handleDelete() {
    setIsDeleting(true);
    try {
      await deleteAssessment(assessmentId);
      toast.success('Assessment deleted.');
      router.push('/dashboard/assessments');
    } catch (error: unknown) {
      if (
        (error as ApiError).response?.data?.detail
          ?.toLowerCase()
          .includes('referenced') ||
        (error as ApiError).response?.status === 409
      ) {
        toast.error('Cannot delete — assessment is referenced by assignments.');
      } else {
        toast.error(extractDetail(error, 'Failed to delete assessment.'));
      }
    } finally {
      setIsDeleting(false);
    }
  }

  // -- Loading state --
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // -- Load error state --
  if (loadError) {
    return (
      <div className="space-y-6 p-6 max-w-4xl mx-auto">
        <Link
          href="/dashboard/assessments"
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Assessments
        </Link>
        <p className="text-sm text-destructive">{loadError}</p>
      </div>
    );
  }

  // -- Not found state --
  if (!assessment) {
    return (
      <div className="space-y-6 p-6 max-w-4xl mx-auto">
        <Link
          href="/dashboard/assessments"
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Assessments
        </Link>
        <p className="text-sm text-muted-foreground">Assessment not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-4xl mx-auto">
      {/* Back link */}
      <Link
        href="/dashboard/assessments"
        className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Assessments
      </Link>

      {/* Header row */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          {assessment.title}
        </h1>
        {assessment.category && (
          <span className="bg-muted text-muted-foreground px-2 py-0.5 rounded text-xs font-medium">
            {assessment.category}
          </span>
        )}
        <span className="bg-muted text-muted-foreground px-2 py-0.5 rounded text-xs font-medium">
          {assessment.gradingMode}
        </span>

        {canManage && (
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() =>
                router.push(`/dashboard/assessments/${assessmentId}/edit`)
              }
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
                  <AlertDialogTitle>Delete Assessment</AlertDialogTitle>
                  <AlertDialogDescription>
                    Are you sure you want to delete this assessment? This action
                    cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={isDeleting}>
                    Cancel
                  </AlertDialogCancel>
                  <AlertDialogAction
                    variant="destructive"
                    disabled={isDeleting}
                    onClick={(e) => {
                      e.preventDefault();
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

      {/* Questions section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-foreground">
          Questions ({assessment.questions.length})
        </h2>

        {assessment.questions.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No questions in this assessment.
          </p>
        )}

        {assessment.questions.map((question, index) => (
          <QuestionCard key={question.questionId} question={question} index={index} />
        ))}
      </div>
    </div>
  );
}

// -- Question Card --

function QuestionCard({ question, index }: { question: Question; index: number }) {
  return (
    <div className="rounded-sm border border-border bg-card p-4 space-y-3">
      {/* Question header */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm font-semibold text-foreground">
          Question {index + 1}
        </span>
        <span className="bg-muted text-muted-foreground px-2 py-0.5 rounded text-xs font-medium">
          {question.type}
        </span>
        <span className="text-sm text-muted-foreground">
          {question.maxPoints} pts
        </span>
      </div>

      {/* Prompt */}
      <p className="text-sm text-foreground">{question.prompt}</p>

      {/* Type-specific details */}
      <QuestionDetails question={question} />
    </div>
  );
}

// -- Type-specific question details --

function QuestionDetails({ question }: { question: Question }) {
  const data = question.data;

  switch (question.type) {
    case 'MULTIPLE_CHOICE':
      return <MultipleChoiceDetails data={data} />;
    case 'SHORT_ANSWER':
      return <ShortAnswerDetails data={data} />;
    case 'NUMBER_SCALE':
      return <NumberScaleDetails question={question} />;
    case 'MOOD_METER':
      return <MoodMeterDetails data={data} />;
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
        <p className="text-xs text-muted-foreground italic">
          (Select all that apply)
        </p>
      )}
      <ol className="list-decimal list-inside space-y-1">
        {data.choices.map((choice, i) => (
          <li key={i} className="text-sm text-foreground">
            &quot;{choice.prompt}&quot;{' '}
            <span className="text-muted-foreground">
              &mdash; {choice.score} pts
            </span>
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
  // data.min/max take precedence, fall back to question.min/max
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

function MoodMeterDetails({ data }: { data: Question['data'] }) {
  if (!data?.labels || data.labels.length === 0) {
    return <p className="text-sm text-muted-foreground">No labels defined.</p>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {data.labels.map((label, i) => (
        <span
          key={i}
          className="bg-muted text-muted-foreground px-2 py-0.5 rounded text-xs font-medium"
        >
          {label}
        </span>
      ))}
    </div>
  );
}
