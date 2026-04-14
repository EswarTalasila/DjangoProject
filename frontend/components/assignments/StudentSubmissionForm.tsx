'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Loader2, Upload, X, ImageIcon } from 'lucide-react';

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
import MoodMeterInput from '@/components/questions/MoodMeterInput';
import type { Question, SubmissionMode } from '@/lib/assignment-template-api';
import type {
  SubmissionStatus,
  SubmissionDTO,
  SubmissionImageDTO,
} from '@/lib/submission-api';
import {
  uploadSubmissionImage,
  listSubmissionImages,
  deleteSubmissionImage,
} from '@/lib/submission-api';
import AssignmentStatusBanner from './AssignmentStatusBanner';

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

const STATUS_LABELS: Record<SubmissionStatus, string> = {
  NOT_STARTED: 'Not Started',
  IN_PROGRESS: 'In Progress',
  SUBMITTED: 'Submitted',
  GRADED: 'Graded',
};

const STATUS_COLORS: Record<SubmissionStatus, string> = {
  NOT_STARTED: 'bg-muted text-muted-foreground',
  IN_PROGRESS: 'bg-status-warning-bg text-foreground',
  SUBMITTED: 'bg-status-success-bg text-foreground',
  GRADED: 'bg-brand-sky text-foreground',
};

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
    case 'MOOD_METER':
      return 'Mood Meter';
    default:
      return kind;
  }
}

function defaultStudentAnswer(_question: Question): StudentAttemptAnswer {
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

function renderStudentResponse(question: Question, answer: StudentAttemptAnswer): string {
  if (question.type === 'MULTIPLE_CHOICE') {
    const choices = question.data?.choices ?? [];
    if (answer.selectedChoiceIndexes.length === 0) return 'No option selected';
    const labels = answer.selectedChoiceIndexes
      .map((idx) => choices[idx]?.prompt || `Choice ${idx + 1}`)
      .filter(Boolean);
    return labels.join(', ');
  }
  if (question.type === 'SHORT_ANSWER') {
    return answer.textResponse.trim() || 'No response';
  }
  if (question.type === 'NUMBER_SCALE') {
    return answer.numericResponse == null ? 'No value selected' : String(answer.numericResponse);
  }
  if (question.type === 'MOOD_METER') {
    return answer.moodSelection ? answer.moodSelection.moodName : 'No mood selected';
  }
  return 'No response';
}

function StudentQuestionPreview({
  question,
  answer,
  readOnly,
  onSelectChoice,
  onTextChange,
  onNumberChange,
  onMoodChange,
}: {
  question: Question;
  answer: StudentAttemptAnswer;
  readOnly?: boolean;
  onSelectChoice: (choiceIndex: number, checked: boolean) => void;
  onTextChange: (nextValue: string) => void;
  onNumberChange: (nextValue: number) => void;
  onMoodChange: (selection: MoodSelection) => void;
}) {
  const data = question.data;

  if (question.type === 'MULTIPLE_CHOICE') {
    const isSelectAll = Boolean(data?.selectAll);
    return (
      <div className="space-y-2">
        {!readOnly && (
          <p className="text-xs text-muted-foreground">
            {isSelectAll ? 'Select all that apply.' : 'Select one option.'}
          </p>
        )}
        {(data?.choices ?? []).map((choice, idx) => (
          <div
            key={`${choice.prompt}-${idx}`}
            className="flex items-center gap-2 rounded border border-border bg-muted/20 px-3 py-2 text-sm"
          >
            {!readOnly && (
              <input
                type={isSelectAll ? 'checkbox' : 'radio'}
                name={`student-preview-q-${question.questionId}`}
                checked={answer.selectedChoiceIndexes.includes(idx)}
                onChange={(event) => onSelectChoice(idx, event.target.checked)}
              />
            )}
            <span className="text-foreground">{choice.prompt || '(empty choice)'}</span>
          </div>
        ))}
      </div>
    );
  }

  if (question.type === 'SHORT_ANSWER') {
    if (readOnly) {
      return (
        <div className="w-full min-h-16 rounded border border-border bg-muted/10 px-3 py-2 text-sm text-muted-foreground italic">
          Response will be provided in uploaded file.
        </div>
      );
    }
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
    if (readOnly) {
      return (
        <p className="text-xs text-muted-foreground">
          Scale: {min} – {max}{data?.target != null ? ` (target: ${data.target})` : ''}
        </p>
      );
    }
    const hasSelected = answer.numericResponse !== null;
    return (
      <div className="space-y-2">
        <input
          type="range"
          min={min}
          max={max}
          value={answer.numericResponse ?? min}
          onChange={(event) => onNumberChange(Number(event.target.value))}
          className={`w-full ${!hasSelected ? 'opacity-40' : ''}`}
        />
        <p className="text-xs text-muted-foreground">
          {hasSelected
            ? `Selected: ${answer.numericResponse} (range ${min}–${max})`
            : `Drag the slider to select a value between ${min} and ${max}`}
        </p>
      </div>
    );
  }

  if (question.type === 'MOOD_METER') {
    return (
      <MoodMeterInput
        value={answer.moodSelection}
        onChange={onMoodChange}
        disabled={readOnly}
      />
    );
  }

  return <p className="text-sm text-muted-foreground">Preview unavailable for this question type.</p>;
}

export type StudentSubmissionFormProps = {
  viewerRole: string;
  assignmentArchived: boolean;
  assignmentNotOpen: boolean;
  openAt: string | null;
  submissionMode: SubmissionMode;
  flatQuestions: Question[];
  studentAnswers: Record<number, StudentAttemptAnswer>;
  studentFlowStage: StudentFlowStage;
  studentSubmittedAt: Date | null;
  clampedStudentQuestionIndex: number;
  activeStudentQuestion: Question | null;
  activeStudentAnswer: StudentAttemptAnswer | null;
  answeredQuestionIds: Set<number>;
  answeredCount: number;
  autoPointsEarned: number;
  totalPoints: number;
  submission: SubmissionDTO | null;
  submissionLocked: boolean;
  submissionStatus: SubmissionStatus;
  studentBlocked: boolean;
  isSubmitting: boolean;
  draftStatus: 'idle' | 'saving' | 'saved' | 'error';
  onStudentQuestionIndexChange: (index: number) => void;
  onUpdateStudentAnswer: (question: Question, updater: (curr: StudentAttemptAnswer) => StudentAttemptAnswer) => void;
  onSubmit: () => void;
  onSetFlowStage: (stage: StudentFlowStage) => void;
  onSetSubmittedAt: (date: Date | null) => void;
};

export default function StudentSubmissionForm({
  viewerRole,
  assignmentArchived,
  assignmentNotOpen,
  openAt,
  submissionMode,
  flatQuestions,
  studentAnswers,
  studentFlowStage,
  studentSubmittedAt,
  clampedStudentQuestionIndex,
  activeStudentQuestion,
  activeStudentAnswer,
  answeredQuestionIds,
  answeredCount,
  autoPointsEarned,
  totalPoints,
  submission,
  submissionLocked,
  submissionStatus,
  studentBlocked,
  isSubmitting,
  draftStatus,
  onStudentQuestionIndexChange,
  onUpdateStudentAnswer,
  onSubmit,
  onSetFlowStage,
  onSetSubmittedAt,
}: StudentSubmissionFormProps) {
  const showUploadPanel = submissionMode === 'UPLOAD_ONLY' || submissionMode === 'DIGITAL_WITH_UPLOAD';
  const isUploadOnly = submissionMode === 'UPLOAD_ONLY';

  // Upload state
  const [uploadedImages, setUploadedImages] = useState<SubmissionImageDTO[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load existing images when submission is available
  useEffect(() => {
    if (!submission?.id || !showUploadPanel) return;
    let cancelled = false;
    listSubmissionImages(submission.id)
      .then((images) => {
        if (!cancelled) setUploadedImages(images);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [submission?.id, showUploadPanel]);

  const handleFileSelect = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0 || !submission?.id) return;
    setIsUploading(true);
    setUploadError(null);
    try {
      for (const file of Array.from(files)) {
        const image = await uploadSubmissionImage(submission.id, file);
        setUploadedImages((prev) => [...prev, image]);
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setUploadError(detail || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }, [submission?.id]);

  const handleRemoveImage = useCallback(async (imageId: string) => {
    if (!submission?.id) return;
    try {
      await deleteSubmissionImage(submission.id, imageId);
      setUploadedImages((prev) => prev.filter((img) => img.id !== imageId));
    } catch {
      setUploadError('Failed to remove image.');
    }
  }, [submission?.id]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    void handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  return (
    <div className="rounded-sm border border-border bg-card overflow-hidden">
      <AssignmentStatusBanner
        viewerRole={viewerRole}
        assignmentArchived={assignmentArchived}
        assignmentNotOpen={assignmentNotOpen}
        openAt={openAt}
      />
      <div className="border-b border-border px-5 py-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-foreground">
            {studentFlowStage === 'submitted' ? 'Submission Review' : 'Assignment'}
          </p>
          <p className="text-xs text-muted-foreground">
            {studentFlowStage === 'submitted'
              ? isUploadOnly
                ? `${uploadedImages.length} file(s) uploaded`
                : `${answeredCount}/${flatQuestions.length} answered`
              : isUploadOnly
                ? 'Upload your work below'
                : `Question ${clampedStudentQuestionIndex + 1} of ${flatQuestions.length}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {viewerRole === 'STUDENT' && draftStatus === 'saving' && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" /> Saving...
            </span>
          )}
          {viewerRole === 'STUDENT' && draftStatus === 'saved' && (
            <span className="text-xs text-muted-foreground">Draft saved</span>
          )}
          {viewerRole === 'STUDENT' && draftStatus === 'error' && (
            <span className="text-xs text-destructive">Save failed</span>
          )}
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[submissionStatus]}`}>
            {STATUS_LABELS[submissionStatus]}
          </span>
        </div>
      </div>

      <div className="grid min-h-[620px] lg:grid-cols-[minmax(0,1fr)_280px]">
        <section className="min-h-0 flex flex-col border-b lg:border-b-0 lg:border-r border-border">
          {/* Upload panel for UPLOAD_ONLY and DIGITAL_WITH_UPLOAD modes */}
          {showUploadPanel && studentFlowStage !== 'submitted' && (
            <div className="p-5 space-y-4 border-b border-border">
              <div>
                <p className="text-sm font-semibold text-foreground">Upload Your Work</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Upload images or files as your submission. Supports JPG, PNG, WebP (max 10MB each).
                </p>
              </div>

              {uploadError && (
                <p className="text-xs text-destructive">{uploadError}</p>
              )}

              {/* Drop zone */}
              {!submissionLocked && !studentBlocked && (
                <div
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border bg-muted/20 py-8 px-4 cursor-pointer hover:border-primary/40 transition-colors"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="h-8 w-8 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    {isUploading ? 'Uploading...' : 'Drop files here or click to upload'}
                  </p>
                  {isUploading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    multiple
                    className="hidden"
                    onChange={(e) => void handleFileSelect(e.target.files)}
                  />
                </div>
              )}

              {/* Uploaded images list */}
              {uploadedImages.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Uploaded Files ({uploadedImages.length})
                  </p>
                  <div className="grid gap-2">
                    {uploadedImages.map((img) => (
                      <div
                        key={img.id}
                        className="flex items-center gap-3 rounded border border-border bg-muted/10 px-3 py-2"
                      >
                        <ImageIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-foreground truncate">{img.originalFilename}</p>
                          <p className="text-xs text-muted-foreground">
                            {(img.sizeBytes / 1024).toFixed(0)} KB
                          </p>
                        </div>
                        {!submissionLocked && !studentBlocked && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-destructive"
                            onClick={() => void handleRemoveImage(img.id)}
                          >
                            <X className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Submit button for upload modes */}
              {showUploadPanel && viewerRole === 'STUDENT' && (
                <div className="flex items-center gap-2 pt-2">
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        type="button"
                        disabled={submissionLocked || studentBlocked || isSubmitting || uploadedImages.length === 0}
                      >
                        {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Submit
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Submit Assignment</AlertDialogTitle>
                        <AlertDialogDescription>
                          Once submitted, you cannot change your uploads.
                          You have uploaded {uploadedImages.length} file(s).
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel disabled={isSubmitting}>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={(event) => {
                            event.preventDefault();
                            onSubmit();
                          }}
                          disabled={isSubmitting}
                        >
                          Confirm Submit
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              )}
            </div>
          )}

          {/* Upload summary in submitted view */}
          {showUploadPanel && studentFlowStage === 'submitted' && uploadedImages.length > 0 && (
            <div className="p-5 border-b border-border space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Uploaded Files ({uploadedImages.length})
              </p>
              <div className="grid gap-2">
                {uploadedImages.map((img) => (
                  <div
                    key={img.id}
                    className="flex items-center gap-3 rounded border border-border bg-muted/10 px-3 py-2"
                  >
                    <ImageIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-foreground truncate">{img.originalFilename}</p>
                      <p className="text-xs text-muted-foreground">
                        {(img.sizeBytes / 1024).toFixed(0)} KB
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Question answering flow — hidden for UPLOAD_ONLY */}
          {!isUploadOnly && studentFlowStage === 'submitted' ? (
            <div className="min-h-0 flex-1 overflow-y-auto p-5 space-y-4">
              <div className="rounded-sm border border-border bg-muted/10 p-4 grid gap-3 sm:grid-cols-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Answered</p>
                  <p className="text-lg font-semibold text-foreground">
                    {answeredCount}/{flatQuestions.length}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    {submission?.status === 'GRADED' ? 'Score' : 'Auto Points (Est.)'}
                  </p>
                  <p className="text-lg font-semibold text-foreground">
                    {submission?.score != null
                      ? `${formatPoints(submission.score)}/${formatPoints(totalPoints)}`
                      : `${formatPoints(autoPointsEarned)}/${formatPoints(totalPoints)}`}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Submitted</p>
                  <p className="text-sm font-semibold text-foreground">
                    {studentSubmittedAt ? studentSubmittedAt.toLocaleString() : '-'}
                  </p>
                </div>
              </div>

              {flatQuestions.map((question, idx) => {
                const answer = studentAnswers[question.questionId] ?? defaultStudentAnswer(question);
                const auto = estimateAutoPoints(question, answer);
                return (
                  <div key={`submitted-${question.questionId}`} className="rounded-sm border border-border bg-card p-4 space-y-2">
                    <p className="text-sm font-semibold text-foreground">
                      Q{idx + 1}. {question.prompt}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatQuestionKind(question.type)} • {formatPoints(question.maxPoints)} pts
                    </p>
                    {question.image && (
                      <figure className="mt-2 rounded-lg border border-border overflow-hidden bg-muted/20">
                        <img
                          src={question.image.url}
                          alt={question.image.originalFilename}
                          className="w-full h-auto max-h-64 object-contain"
                        />
                      </figure>
                    )}
                    <p className="text-sm text-foreground">
                      <span className="font-medium">Response:</span> {renderStudentResponse(question, answer)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {auto == null
                        ? 'Manual grading required'
                        : `Auto points preview: ${formatPoints(auto)} / ${formatPoints(question.maxPoints)}`}
                    </p>
                  </div>
                );
              })}
            </div>
          ) : activeStudentQuestion ? (
            <>
              <div className="px-5 py-4 border-b border-border bg-muted/10">
                <p className="text-sm font-semibold text-foreground">
                  Q{clampedStudentQuestionIndex + 1}. {activeStudentQuestion.prompt}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {formatQuestionKind(activeStudentQuestion.type)} •{' '}
                  {formatPoints(activeStudentQuestion.maxPoints)} pts
                </p>
                {activeStudentQuestion.image && (
                  <figure className="mt-3 rounded-lg border border-border overflow-hidden bg-muted/20">
                    <img
                      src={activeStudentQuestion.image.url}
                      alt={activeStudentQuestion.image.originalFilename}
                      className="w-full h-auto max-h-80 object-contain"
                    />
                    <figcaption className="text-[10px] text-muted-foreground px-3 py-1.5 border-t border-border">
                      {activeStudentQuestion.image.originalFilename}
                    </figcaption>
                  </figure>
                )}
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto p-5">
                <div className="max-w-3xl">
                  {activeStudentAnswer && (
                    <StudentQuestionPreview
                      question={activeStudentQuestion}
                      answer={activeStudentAnswer}
                      readOnly={showUploadPanel}
                      onSelectChoice={(choiceIndex, checked) => {
                        onUpdateStudentAnswer(activeStudentQuestion, (curr) => {
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
                        onUpdateStudentAnswer(activeStudentQuestion, (curr) => ({
                          ...curr,
                          textResponse: nextValue,
                        }));
                      }}
                      onNumberChange={(nextValue) => {
                        onUpdateStudentAnswer(activeStudentQuestion, (curr) => ({
                          ...curr,
                          numericResponse: nextValue,
                        }));
                      }}
                      onMoodChange={(selection) => {
                        onUpdateStudentAnswer(activeStudentQuestion, (curr) => ({
                          ...curr,
                          moodSelection: selection,
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
                    onStudentQuestionIndexChange(Math.max(0, clampedStudentQuestionIndex - 1))
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
                      onStudentQuestionIndexChange(
                        Math.min(flatQuestions.length - 1, clampedStudentQuestionIndex + 1),
                      )
                    }
                    disabled={clampedStudentQuestionIndex >= flatQuestions.length - 1}
                  >
                    Next
                  </Button>
                  {viewerRole === 'STUDENT' && !showUploadPanel && (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          type="button"
                          disabled={submissionLocked || studentBlocked || isSubmitting}
                        >
                          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                          Submit
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Submit Assignment</AlertDialogTitle>
                          <AlertDialogDescription>
                            Once submitted, you cannot change your answers.
                            You have answered {answeredCount} of {flatQuestions.length} questions.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel disabled={isSubmitting}>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={(event) => {
                              event.preventDefault();
                              onSubmit();
                            }}
                            disabled={isSubmitting}
                          >
                            Confirm Submit
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  )}
                  {viewerRole !== 'STUDENT' && (
                    <Button
                      type="button"
                      onClick={() => {
                        onSetFlowStage('submitted');
                        onSetSubmittedAt(new Date());
                      }}
                    >
                      Submit (Preview)
                    </Button>
                  )}
                </div>
              </div>
            </>
          ) : null}
        </section>

        <aside className="p-4 bg-muted/20 hidden lg:block">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
            {studentFlowStage === 'submitted' ? 'Submission Map' : 'Question Navigator'}
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
                  onClick={() => onStudentQuestionIndexChange(idx)}
                >
                  Q{idx + 1}{isAnswered ? ' •' : ''}
                </Button>
              );
            })}
          </div>
          {studentFlowStage === 'submitted' && !submissionLocked && (
            <Button
              type="button"
              variant="outline"
              className="w-full mt-3"
              onClick={() => onSetFlowStage('attempt')}
            >
              Return To Attempt
            </Button>
          )}
        </aside>
      </div>
    </div>
  );
}
