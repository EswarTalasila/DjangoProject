import api from '@/lib/api';

export type AudienceType = 'COURSE' | 'TEACHER';
export type AssignmentStatus = 'ACTIVE' | 'ARCHIVED';

export type Assignment = {
  id: number;
  assessmentId: number;
  audienceType: AudienceType;
  courseId: number | null;
  targetTeacherId: number | null;
  openAt: string | null;
  dueAt: string | null;
  status: AssignmentStatus;
};

export type AssignmentCreateInput = {
  assessmentId: number;
  audienceType: 'COURSE';
  courseId: number;
  openAt: string;
  dueAt?: string | null;
};

export type AssignmentUpdateInput = {
  openAt?: string;
  dueAt?: string | null;
};

type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export async function createAssignment(payload: AssignmentCreateInput): Promise<Assignment> {
  const response = await api.post<Assignment>('/assignments', payload);
  return response.data;
}

export async function getAssignment(assignmentId: number): Promise<Assignment> {
  const response = await api.get<Assignment>(`/assignments/${assignmentId}`);
  return response.data;
}

export async function updateAssignment(
  assignmentId: number,
  payload: AssignmentUpdateInput,
): Promise<Assignment> {
  const response = await api.patch<Assignment>(`/assignments/${assignmentId}`, payload);
  return response.data;
}

export async function deleteAssignment(assignmentId: number): Promise<void> {
  await api.delete(`/assignments/${assignmentId}`);
}

export async function archiveAssignment(assignmentId: number): Promise<Assignment> {
  const response = await api.post<Assignment>(`/assignments/${assignmentId}/archive`, {});
  return response.data;
}

export async function listAssignmentsByCourse(courseId: number): Promise<Assignment[]> {
  const response = await api.get<Paginated<Assignment> | Assignment[]>(`/assignments/courses/${courseId}`);
  const data = response.data;
  return Array.isArray(data) ? data : data.results;
}

export async function listAssignmentsForUser(userId: string | number): Promise<Assignment[]> {
  const response = await api.get<Paginated<Assignment> | Assignment[]>(`/assignments/users/${userId}`);
  const data = response.data;
  return Array.isArray(data) ? data : data.results;
}
