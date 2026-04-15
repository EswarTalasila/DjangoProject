import api, { type ApiRequestOptions } from '@/lib/api';

// -- Types --

export type GradingMode = 'AUTO' | 'MANUAL' | 'HYBRID';
export type GradingStrategy = 'AUTO' | 'MANUAL';
export type ScoringPolicy = 'STANDARD' | 'COMPLETION';
export type QuestionKind = 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'NUMBER_SCALE' | 'MOOD_METER' | 'FILE_UPLOAD';
export type SubmissionMode = 'DIGITAL' | 'UPLOAD_ONLY' | 'DIGITAL_WITH_UPLOAD';

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

export type AssignmentTemplateStatus = 'ACTIVE' | 'ARCHIVED' | 'DRAFT';

export type AssignmentTemplate = {
  id: number;
  title: string;
  category: string | null;
  gradingMode: GradingMode;
  scoringPolicy: ScoringPolicy;
  submissionMode: SubmissionMode;
  questions: Question[];
  questionGroups: QuestionGroup[];
  rubricId: number | null;
  rubricAssignmentTemplateIds: number[];
  status?: AssignmentTemplateStatus;
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

export type AssignmentTemplateInput = {
  title: string;
  category?: string | null;
  gradingMode: GradingMode;
  scoringPolicy?: ScoringPolicy;
  submissionMode?: SubmissionMode;
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

type ListAssignmentTemplatesOptions = {
  includeArchived?: boolean;
};

// -- API Functions --

/** GET /assignment-templates/ — Fetch all assignment templates (paginated). */
export async function listAssignmentTemplates(
  options?: ListAssignmentTemplatesOptions,
): Promise<AssignmentTemplate[]> {
  const params = new URLSearchParams();
  if (options?.includeArchived) {
    params.set('includeArchived', 'true');
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : '';
  const response = await api.get<Paginated<AssignmentTemplate>>(`/assignment-templates/${suffix}`);
  return response.data.results;
}

/** GET /assignment-templates/:id — Fetch a single assignment template by ID. */
export async function getAssignmentTemplate(id: number): Promise<AssignmentTemplate> {
  const response = await api.get<AssignmentTemplate>(`/assignment-templates/${id}`);
  return response.data;
}

/** POST /assignment-templates/ — Create a new assignment template. */
export async function createAssignmentTemplate(payload: AssignmentTemplateInput): Promise<AssignmentTemplate> {
  const response = await api.post<AssignmentTemplate>('/assignment-templates/', payload);
  return response.data;
}

/** PATCH /assignment-templates/:id — Partially update an existing assignment template. */
export async function updateAssignmentTemplate(
  id: number,
  payload: AssignmentTemplateInput,
  options?: ApiRequestOptions,
): Promise<AssignmentTemplate> {
  const response = await api.patch<AssignmentTemplate>(`/assignment-templates/${id}`, payload, options);
  return response.data;
}

/** DELETE /assignment-templates/:id — Permanently delete an assignment template. */
export async function deleteAssignmentTemplate(id: number): Promise<void> {
  await api.delete(`/assignment-templates/${id}`);
}

/** DELETE /assignment-templates/:id?purge=true — Permanently delete an archived assignment template. */
export async function purgeAssignmentTemplate(id: number): Promise<void> {
  await api.delete(`/assignment-templates/${id}?purge=true`);
}

/** POST /assignment-templates/:id/archive — Soft-archive an assignment template. */
export async function archiveAssignmentTemplate(id: number): Promise<AssignmentTemplate> {
  const response = await api.post<AssignmentTemplate>(`/assignment-templates/${id}/archive`, {});
  return response.data;
}

/** POST /assignment-templates/:id/restore — Restore a previously archived assignment template. */
export async function restoreAssignmentTemplate(id: number): Promise<AssignmentTemplate> {
  const response = await api.post<AssignmentTemplate>(`/assignment-templates/${id}/restore`, {});
  return response.data;
}

/** POST /assignment-templates/?draft=true — Create an empty draft assignment template. */
export async function createDraftAssignmentTemplate(): Promise<AssignmentTemplate> {
  const response = await api.post<AssignmentTemplate>('/assignment-templates/?draft=true', {});
  return response.data;
}

/** POST /assignment-templates/:id/publish — Publish a draft assignment template. */
export async function publishAssignmentTemplate(id: number): Promise<AssignmentTemplate> {
  const response = await api.post<AssignmentTemplate>(`/assignment-templates/${id}/publish`, {});
  return response.data;
}

/** POST /assignment-templates/:assignmentTemplateId/questions/:questionId/image — Upload question image. */
export async function uploadQuestionImage(
  assignmentTemplateId: number,
  questionId: number,
  file: File,
): Promise<QuestionImage> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<QuestionImage>(
    `/assignment-templates/${assignmentTemplateId}/questions/${questionId}/image`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return response.data;
}

/** DELETE /assignment-templates/:assignmentTemplateId/questions/:questionId/image — Remove question image. */
export async function deleteQuestionImage(
  assignmentTemplateId: number,
  questionId: number,
): Promise<void> {
  await api.delete(
    `/assignment-templates/${assignmentTemplateId}/questions/${questionId}/image`,
  );
}
