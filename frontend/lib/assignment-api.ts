import api from '@/lib/api';
import type {
  QuestionData,
  QuestionGroup,
  QuestionImage,
  QuestionKind,
} from '@/lib/assignment-template-api';

export type AudienceType = 'COURSE' | 'TEACHER';
export type AssignmentStatus = 'ACTIVE' | 'ARCHIVED';

export type Assignment = {
  id: number;
  title: string;
  assignmentTemplateId: number;
  assignmentTemplateTitle: string | null;
  audienceType: AudienceType;
  courseId: number | null;
  targetTeacherId: number | null;
  openAt: string | null;
  dueAt: string | null;
  status: AssignmentStatus;
};

export type AssignmentArchiveArtifact = {
  id: number;
  assignmentId: number;
  identifiable: boolean;
  filename: string;
  sizeBytes: number;
  sha256Hash: string;
  generatedAt: string | null;
  generatedByUserId: number | null;
  manifest: Record<string, unknown>;
};

export type AssignmentQuestionOrigin = 'TEMPLATE' | 'TEACHER_ADDITION';

export type AssignmentQuestion = {
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
  gradingStrategy: 'AUTO' | 'MANUAL';
  orderIndex: number;
  origin: AssignmentQuestionOrigin | null;
  lockedFromSource: boolean;
  sourceQuestionId: number | null;
};

export type AssignmentTeacherCriterion = {
  id: number;
  title: string;
  description: string;
  weight: number;
  orderIndex: number;
};

export type AssignmentContent = {
  id: number;
  title: string;
  assignmentId: number;
  assignmentTemplateId: number;
  assignmentTemplateTitle: string;
  category: string | null;
  gradingMode: string;
  scoringPolicy: string;
  submissionMode: string;
  rubricId: number | null;
  questions: AssignmentQuestion[];
  questionGroups: QuestionGroup[];
  teacherCriteria: AssignmentTeacherCriterion[];
};

export type AssignmentCreateInput = {
  title?: string;
  assignmentTemplateId: number;
  audienceType: 'COURSE';
  courseId: number;
  openAt: string;
  dueAt?: string | null;
};

export type AssignmentUpdateInput = {
  title?: string;
  openAt?: string;
  dueAt?: string | null;
};

export type AssignmentQuestionCreateInput = {
  type: QuestionKind;
  prompt: string;
  maxPoints: number;
  data?: QuestionData;
  gradingStrategy?: 'AUTO' | 'MANUAL';
};

export type AssignmentTeacherCriterionInput = {
  title: string;
  description?: string;
  weight: number;
};

type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

/** POST /assignments/ — Create a new assignment linking an assignment template to a course. */
export async function createAssignment(payload: AssignmentCreateInput): Promise<Assignment> {
  const response = await api.post<Assignment>('/assignments/', payload);
  return response.data;
}

/** GET /assignments/:id — Fetch a single assignment by ID. */
export async function getAssignment(assignmentId: number): Promise<Assignment> {
  const response = await api.get<Assignment>(`/assignments/${assignmentId}`);
  return response.data;
}

/** GET /assignments/:id/template — Fetch the effective assignment content snapshot. */
export async function getAssignmentContent(assignmentId: number): Promise<AssignmentContent> {
  const response = await api.get<AssignmentContent>(`/assignments/${assignmentId}/template`);
  return response.data;
}

/** PATCH /assignments/:id — Update assignment schedule or title. */
export async function updateAssignment(
  assignmentId: number,
  payload: AssignmentUpdateInput,
): Promise<Assignment> {
  const response = await api.patch<Assignment>(`/assignments/${assignmentId}`, payload);
  return response.data;
}

/** DELETE /assignments/:id?purge=true — Permanently delete an archived assignment. */
export async function purgeAssignment(assignmentId: number): Promise<void> {
  await api.delete(`/assignments/${assignmentId}?purge=true`);
}

/** POST /assignments/:id/archive — Soft-archive an assignment. */
export async function archiveAssignment(assignmentId: number): Promise<Assignment> {
  const response = await api.post<Assignment>(`/assignments/${assignmentId}/archive`, {});
  return response.data;
}

/** POST /assignments/:id/restore — Restore a previously archived assignment. */
export async function restoreAssignment(assignmentId: number): Promise<Assignment> {
  const response = await api.post<Assignment>(`/assignments/${assignmentId}/restore`, {});
  return response.data;
}

/** POST /assignments/:id/questions — Add a teacher-authored question to an assignment. */
export async function addAssignmentQuestion(
  assignmentId: number,
  payload: AssignmentQuestionCreateInput,
): Promise<AssignmentContent> {
  const response = await api.post<AssignmentContent>(`/assignments/${assignmentId}/questions`, payload);
  return response.data;
}

/** POST /assignments/:id/teacher-criteria — Add a teacher-authored criterion to an assignment. */
export async function addAssignmentTeacherCriterion(
  assignmentId: number,
  payload: AssignmentTeacherCriterionInput,
): Promise<AssignmentContent> {
  const response = await api.post<AssignmentContent>(
    `/assignments/${assignmentId}/teacher-criteria`,
    payload,
  );
  return response.data;
}

/** GET /assignments/:id/images — List reusable question images visible from the assignment context. */
export async function listReusableAssignmentImages(assignmentId: number): Promise<QuestionImage[]> {
  const response = await api.get<QuestionImage[]>(`/assignments/${assignmentId}/images`);
  return response.data;
}

/** POST /assignments/:assignmentId/questions/:questionId/image — Upload question image. */
export async function uploadAssignmentQuestionImage(
  assignmentId: number,
  questionId: number,
  file: File,
): Promise<QuestionImage> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<QuestionImage>(
    `/assignments/${assignmentId}/questions/${questionId}/image`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return response.data;
}

/** POST /assignments/:assignmentId/questions/:questionId/image/reuse — Attach a previous image. */
export async function reuseAssignmentQuestionImage(
  assignmentId: number,
  questionId: number,
  assetId: string,
): Promise<QuestionImage> {
  const response = await api.post<QuestionImage>(
    `/assignments/${assignmentId}/questions/${questionId}/image/reuse`,
    { assetId },
  );
  return response.data;
}

/** DELETE /assignments/:assignmentId/questions/:questionId/image — Remove assignment question image. */
export async function deleteAssignmentQuestionImage(
  assignmentId: number,
  questionId: number,
): Promise<void> {
  await api.delete(`/assignments/${assignmentId}/questions/${questionId}/image`);
}

/** GET /assignments/:id/archive-bundle — Fetch archive bundle metadata for an archived assignment. */
export async function getAssignmentArchiveBundle(
  assignmentId: number,
  options?: { identifiable?: boolean },
): Promise<AssignmentArchiveArtifact> {
  const params = options?.identifiable === undefined ? undefined : { identifiable: options.identifiable };
  const response = await api.get<AssignmentArchiveArtifact>(`/assignments/${assignmentId}/archive-bundle`, { params });
  return response.data;
}

/** POST /assignments/:id/archive-bundle — Generate or replace an archived assignment bundle. */
export async function generateAssignmentArchiveBundle(
  assignmentId: number,
  options?: { identifiable?: boolean },
): Promise<AssignmentArchiveArtifact> {
  const params = options?.identifiable === undefined ? undefined : { identifiable: options.identifiable };
  const response = await api.post<AssignmentArchiveArtifact>(
    `/assignments/${assignmentId}/archive-bundle`,
    {},
    { params },
  );
  return response.data;
}

/** GET /assignments/:id/archive-bundle/download — Download an archived assignment bundle ZIP. */
export async function downloadAssignmentArchiveBundle(
  assignmentId: number,
  options?: { identifiable?: boolean },
): Promise<{ blob: Blob; filename: string }> {
  const params = options?.identifiable === undefined ? undefined : { identifiable: options.identifiable };
  const response = await api.get<Blob>(`/assignments/${assignmentId}/archive-bundle/download`, {
    params,
    responseType: 'blob',
  });
  const disposition = response.headers['content-disposition'] as string | undefined;
  const match = disposition?.match(/filename="?([^"]+)"?/i);
  return {
    blob: response.data,
    filename: match?.[1] ?? `assignment-${assignmentId}-archive.zip`,
  };
}

/** GET /assignments/courses/:id — List assignments for a given course. */
export async function listAssignmentsByCourse(
  courseId: number,
  options?: { includeArchived?: boolean },
): Promise<Assignment[]> {
  const params = options?.includeArchived ? { includeArchived: true } : undefined;
  const response = await api.get<Paginated<Assignment> | Assignment[]>(
    `/assignments/courses/${courseId}`,
    { params },
  );
  const data = response.data;
  return Array.isArray(data) ? data : data.results;
}

/** GET /assignments/users/:id — List all assignments visible to a specific user. */
export async function listAssignmentsForUser(userId: string | number): Promise<Assignment[]> {
  const response = await api.get<Paginated<Assignment> | Assignment[]>(`/assignments/users/${userId}`);
  const data = response.data;
  return Array.isArray(data) ? data : data.results;
}
