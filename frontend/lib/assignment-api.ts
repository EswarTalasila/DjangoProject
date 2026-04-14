import api from '@/lib/api';

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

/** PATCH /assignments/:id — Update assignment schedule or title. */
export async function updateAssignment(
  assignmentId: number,
  payload: AssignmentUpdateInput,
): Promise<Assignment> {
  const response = await api.patch<Assignment>(`/assignments/${assignmentId}`, payload);
  return response.data;
}

/** DELETE /assignments/:id — Permanently delete an assignment. */
export async function deleteAssignment(assignmentId: number): Promise<void> {
  await api.delete(`/assignments/${assignmentId}`);
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

/** GET /assignments/courses/:id — List all assignments for a given course. */
export async function listAssignmentsByCourse(courseId: number): Promise<Assignment[]> {
  const response = await api.get<Paginated<Assignment> | Assignment[]>(`/assignments/courses/${courseId}`);
  const data = response.data;
  return Array.isArray(data) ? data : data.results;
}

/** GET /assignments/users/:id — List all assignments visible to a specific user. */
export async function listAssignmentsForUser(userId: string | number): Promise<Assignment[]> {
  const response = await api.get<Paginated<Assignment> | Assignment[]>(`/assignments/users/${userId}`);
  const data = response.data;
  return Array.isArray(data) ? data : data.results;
}
