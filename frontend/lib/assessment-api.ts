import api, { type ApiRequestOptions } from '@/lib/api';

// -- Types --

export type GradingMode = 'AUTO' | 'MANUAL' | 'HYBRID';
export type GradingStrategy = 'AUTO' | 'MANUAL';
export type ScoringPolicy = 'STANDARD' | 'COMPLETION';
export type QuestionKind = 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'NUMBER_SCALE' | 'MOOD_METER' | 'FILE_UPLOAD';

export type McqChoice = {
  prompt: string;
  score: number;
};

export type QuestionData = {
  choices?: McqChoice[];
  selectAll?: boolean;
  caseSensitive?: boolean;
  trim?: boolean;
  min?: number;
  max?: number;
  target?: number | null;
};

export type QuestionImage = {
  id: string;
  storageKey: string;
  url: string;
  originalFilename: string;
  mimeType: string;
  sizeBytes: number;
};

export type QuestionGroup = {
  id: number;
  name: string;
  rubricId: number | null;
  orderIndex: number;
};

export type Question = {
  questionId: number;
  id: number;
  type: QuestionKind;
  prompt: string;
  maxPoints: number;
  autoGradable: boolean;
  graded: boolean;
  image: QuestionImage | null;
  data: QuestionData | null;
  selectAll: boolean | null;
  min: number | null;
  max: number | null;
  groupId: number | null;
  rubricId: number | null;
  gradingStrategy: GradingStrategy;
};

export type AssessmentStatus = 'ACTIVE' | 'ARCHIVED' | 'DRAFT';

export type Assessment = {
  id: number;
  title: string;
  category: string | null;
  gradingMode: GradingMode;
  scoringPolicy: ScoringPolicy;
  questions: Question[];
  questionGroups: QuestionGroup[];
  rubricId: number | null;
  rubricAssessmentIds: number[];
  status?: AssessmentStatus;
};

export type QuestionGroupInput = {
  clientKey: string;
  name: string;
  rubricId?: number | null;
};

export type QuestionInput = {
  type: QuestionKind;
  prompt: string;
  maxPoints: number;
  data?: QuestionData;
  groupClientKey?: string;
  rubricId?: number | null;
  gradingStrategy?: GradingStrategy;
  /** Image metadata (structured locally, serialized for backend) */
  questionImage?: QuestionImage | null;
};

export type AssessmentInput = {
  title: string;
  category?: string | null;
  gradingMode: GradingMode;
  scoringPolicy?: ScoringPolicy;
  rubricId?: number | null;
  questions: QuestionInput[];
  questionGroups?: QuestionGroupInput[];
};

type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

// -- API Functions --

/** GET /assessments/ — Fetch all assessments (paginated, returns results array). */
export async function listAssessments(): Promise<Assessment[]> {
  const response = await api.get<Paginated<Assessment>>('/assessments/');
  return response.data.results;
}

/** GET /assessments/:id — Fetch a single assessment by ID. */
export async function getAssessment(id: number): Promise<Assessment> {
  const response = await api.get<Assessment>(`/assessments/${id}`);
  return response.data;
}

/** POST /assessments/ — Create a new assessment with questions and optional groups. */
export async function createAssessment(payload: AssessmentInput): Promise<Assessment> {
  const response = await api.post<Assessment>('/assessments/', payload);
  return response.data;
}

/** PATCH /assessments/:id — Partially update an existing assessment. */
export async function updateAssessment(
  id: number,
  payload: AssessmentInput,
  options?: ApiRequestOptions,
): Promise<Assessment> {
  const response = await api.patch<Assessment>(`/assessments/${id}`, payload, options);
  return response.data;
}

/** DELETE /assessments/:id — Permanently delete an assessment. */
export async function deleteAssessment(id: number): Promise<void> {
  await api.delete(`/assessments/${id}`);
}

/** POST /assessments/:id/archive — Soft-archive an assessment. */
export async function archiveAssessment(id: number): Promise<Assessment> {
  const response = await api.post<Assessment>(`/assessments/${id}/archive`, {});
  return response.data;
}

/** POST /assessments/:id/restore — Restore a previously archived assessment. */
export async function restoreAssessment(id: number): Promise<Assessment> {
  const response = await api.post<Assessment>(`/assessments/${id}/restore`, {});
  return response.data;
}

/** POST /assessments/?draft=true — Create an empty draft assessment. */
export async function createDraft(): Promise<Assessment> {
  const response = await api.post<Assessment>('/assessments/?draft=true', {});
  return response.data;
}

/** POST /assessments/:id/publish — Publish a draft assessment. */
export async function publishAssessment(id: number): Promise<Assessment> {
  const response = await api.post<Assessment>(`/assessments/${id}/publish`, {});
  return response.data;
}

/** POST /assessments/:assessmentId/questions/:questionId/image — Upload question image. */
export async function uploadQuestionImage(
  assessmentId: number,
  questionId: number,
  file: File,
): Promise<QuestionImage> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<QuestionImage>(
    `/assessments/${assessmentId}/questions/${questionId}/image`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return response.data;
}

/** DELETE /assessments/:assessmentId/questions/:questionId/image — Remove question image. */
export async function deleteQuestionImage(
  assessmentId: number,
  questionId: number,
): Promise<void> {
  await api.delete(
    `/assessments/${assessmentId}/questions/${questionId}/image`,
  );
}
