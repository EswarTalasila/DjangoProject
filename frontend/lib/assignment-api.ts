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
