import api from '@/lib/api';

export type WorkspaceStatus = 'DRAFT' | 'SEALED';
export type NodeType = 'FOLDER' | 'FILE';
export type DatasetBinding = 'ROSTER' | 'COURSE_SUBMISSIONS' | 'CROSS_COURSE_SUBMISSIONS';
export type BuildStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export type PackageNode = {
  id: number;
  parentId: number | null;
  nodeType: NodeType;
  label: string;
  orderIndex: number;
  datasetBinding: DatasetBinding | null;
  bindingCourseId: number | null;
  filters: Record<string, unknown> | null;
  identifiable: boolean;
  includeAnswers: boolean;
};

export type PackageWorkspace = {
  id: number;
  name: string;
  description: string;
  status: WorkspaceStatus;
  scopeCourseId: number | null;
  revision: number;
  createdBy: number;
  createdAt: string;
  updatedAt: string;
  nodes: PackageNode[];
};

export type ValidationIssue = {
  nodeId: number | null;
  code: string;
  message: string;
};

export type ValidationResult = {
  valid: boolean;
  violations: ValidationIssue[];
  warnings: ValidationIssue[];
  fileCount: number;
  estimatedRows: number;
};

export type BuildJob = {
  id: number;
  workspaceId: number;
  status: BuildStatus;
  strictMode: boolean;
  mode: 'live' | 'snapshot';
  snapshotId: number | null;
  createdBy: number;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  warnings?: ValidationIssue[];
  errorMessage?: string;
  artifactId?: number;
};

export type WorkspaceSummary = {
  id: number;
  name: string;
  description: string;
  status: WorkspaceStatus;
  scopeCourseId: number | null;
  revision: number;
  createdBy: number;
  createdAt: string;
  updatedAt: string;
  nodeCount: number;
};

export type CreateWorkspacePayload = {
  name: string;
  description?: string;
  scopeCourseId?: number | null;
};

export type UpdateWorkspacePayload = {
  name?: string;
  description?: string;
  status?: WorkspaceStatus;
};

export type AddNodePayload = {
  parentId?: number | null;
  nodeType: NodeType;
  label: string;
  orderIndex?: number;
  datasetBinding?: DatasetBinding | null;
  bindingCourseId?: number | null;
  filters?: Record<string, unknown> | null;
  identifiable?: boolean;
  includeAnswers?: boolean;
};

export type UpdateNodePayload = {
  parentId?: number | null;
  label?: string;
  orderIndex?: number;
  datasetBinding?: DatasetBinding | null;
  bindingCourseId?: number | null;
  filters?: Record<string, unknown> | null;
  identifiable?: boolean;
  includeAnswers?: boolean;
};

export async function listWorkspaces(): Promise<PackageWorkspace[]> {
  const { data } = await api.get<PackageWorkspace[]>('/packages/workspaces');
  return data;
}

export async function createWorkspace(payload: CreateWorkspacePayload): Promise<PackageWorkspace> {
  const { data } = await api.post<PackageWorkspace>('/packages/workspaces', payload);
  return data;
}

export async function getWorkspace(workspaceId: number): Promise<PackageWorkspace> {
  const { data } = await api.get<PackageWorkspace>(`/packages/workspaces/${workspaceId}`);
  return data;
}

export async function updateWorkspace(
  workspaceId: number,
  payload: UpdateWorkspacePayload,
): Promise<PackageWorkspace> {
  const { data } = await api.patch<PackageWorkspace>(`/packages/workspaces/${workspaceId}`, payload);
  return data;
}

export async function addNode(workspaceId: number, payload: AddNodePayload): Promise<PackageNode> {
  const { data } = await api.post<PackageNode>(`/packages/workspaces/${workspaceId}/nodes`, payload);
  return data;
}

export async function updateNode(
  workspaceId: number,
  nodeId: number,
  payload: UpdateNodePayload,
): Promise<PackageNode> {
  const { data } = await api.patch<PackageNode>(
    `/packages/workspaces/${workspaceId}/nodes/${nodeId}`,
    payload,
  );
  return data;
}

export async function deleteNode(workspaceId: number, nodeId: number): Promise<void> {
  await api.delete(`/packages/workspaces/${workspaceId}/nodes/${nodeId}`);
}

export async function validateWorkspace(
  workspaceId: number,
  payload?: { strictMode?: boolean; snapshotId?: number | null },
): Promise<ValidationResult> {
  const { data } = await api.post<ValidationResult>(
    `/packages/workspaces/${workspaceId}/validate`,
    payload ?? {},
  );
  return data;
}

export async function buildWorkspace(
  workspaceId: number,
  payload?: { strictMode?: boolean; snapshotId?: number | null },
): Promise<BuildJob> {
  const { data } = await api.post<BuildJob>(`/packages/workspaces/${workspaceId}/build`, payload ?? {});
  return data;
}

export async function getBuildJob(jobId: number): Promise<BuildJob> {
  const { data } = await api.get<BuildJob>(`/packages/jobs/${jobId}`);
  return data;
}

export async function downloadArtifact(artifactId: number): Promise<{ blob: Blob; filename: string }> {
  const response = await api.get(`/packages/artifacts/${artifactId}/download`, {
    responseType: 'blob',
  });
  const contentDisposition = response.headers['content-disposition'] as string | undefined;
  const filenameMatch = contentDisposition?.match(/filename=\"?([^\";]+)\"?/i);
  return {
    blob: response.data as Blob,
    filename: filenameMatch?.[1] || `package-artifact-${artifactId}.zip`,
  };
}

