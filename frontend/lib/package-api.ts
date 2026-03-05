import api from '@/lib/api';

export type WorkspaceStatus = 'DRAFT' | 'SEALED';
export type NodeType = 'FOLDER' | 'FILE';
export type DatasetBinding = 'ROSTER' | 'COURSE_SUBMISSIONS';
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
  sourceType: NodeSourceType;
  snapshotId: number | null;
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

export type SnapshotStatus = 'QUEUED' | 'READY' | 'FAILED' | 'EXPIRED';
export type NodeSourceType = 'LIVE' | 'SNAPSHOT';

export type DataSnapshot = {
  id: number;
  workspaceId: number;
  datasetBinding: DatasetBinding;
  scopeCourseId: number | null;
  filters: Record<string, unknown> | null;
  includeAnswers: boolean;
  identifiable: boolean;
  rowCount: number;
  fileSize: number;
  checksumSha256: string;
  status: SnapshotStatus;
  errorMessage: string;
  metadata: Record<string, unknown>;
  expiresAt: string | null;
  createdAt: string;
  createdBy: number;
};

export type CreateSnapshotPayload = {
  datasetBinding: DatasetBinding;
  scopeCourseId?: number | null;
  filters?: Record<string, unknown> | null;
  includeAnswers?: boolean;
  identifiable?: boolean;
};

export type ReorderNodePayload = {
  movedNodeId: number;
  targetParentId: number | null;
  targetOrderIndex: number;
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
  sourceType?: NodeSourceType;
  snapshotId?: number | null;
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
  sourceType?: NodeSourceType;
  snapshotId?: number | null;
};

/** GET /packages/workspaces — List all package workspaces. */
export async function listWorkspaces(): Promise<PackageWorkspace[]> {
  const { data } = await api.get<PackageWorkspace[]>('/packages/workspaces');
  return data;
}

/** POST /packages/workspaces — Create a new package workspace. */
export async function createWorkspace(payload: CreateWorkspacePayload): Promise<PackageWorkspace> {
  const { data } = await api.post<PackageWorkspace>('/packages/workspaces', payload);
  return data;
}

/** GET /packages/workspaces/:id — Fetch a single workspace with its node tree. */
export async function getWorkspace(workspaceId: number): Promise<PackageWorkspace> {
  const { data } = await api.get<PackageWorkspace>(`/packages/workspaces/${workspaceId}`);
  return data;
}

/** PATCH /packages/workspaces/:id — Update workspace metadata or status. */
export async function updateWorkspace(
  workspaceId: number,
  payload: UpdateWorkspacePayload,
): Promise<PackageWorkspace> {
  const { data } = await api.patch<PackageWorkspace>(`/packages/workspaces/${workspaceId}`, payload);
  return data;
}

/** POST /packages/workspaces/:id/nodes — Add a file or folder node to a workspace. */
export async function addNode(workspaceId: number, payload: AddNodePayload): Promise<PackageNode> {
  const { data } = await api.post<PackageNode>(`/packages/workspaces/${workspaceId}/nodes`, payload);
  return data;
}

/** PATCH /packages/workspaces/:wid/nodes/:nid — Update properties of an existing node. */
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

/** DELETE /packages/workspaces/:wid/nodes/:nid — Remove a node from a workspace. */
export async function deleteNode(workspaceId: number, nodeId: number): Promise<void> {
  await api.delete(`/packages/workspaces/${workspaceId}/nodes/${nodeId}`);
}

/** POST /packages/workspaces/:id/validate — Run pre-build validation on a workspace. */
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

/** POST /packages/workspaces/:id/build — Start a build job to produce a downloadable archive. */
export async function buildWorkspace(
  workspaceId: number,
  payload?: {
    strictMode?: boolean;
    snapshotId?: number | null;
    includeMetadataFiles?: boolean;
  },
): Promise<BuildJob> {
  const { data } = await api.post<BuildJob>(`/packages/workspaces/${workspaceId}/build`, payload ?? {});
  return data;
}

/** GET /packages/jobs/:id — Poll the status of a build job. */
export async function getBuildJob(jobId: number): Promise<BuildJob> {
  const { data } = await api.get<BuildJob>(`/packages/jobs/${jobId}`);
  return data;
}

/** GET /packages/artifacts/:id/download — Download a completed build artifact as a zip blob. */
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

/** POST /packages/workspaces/:id/snapshots — Capture a point-in-time data snapshot for a workspace. */
export async function createSnapshot(
  workspaceId: number,
  payload: CreateSnapshotPayload,
): Promise<DataSnapshot> {
  const { data } = await api.post<DataSnapshot>(
    `/packages/workspaces/${workspaceId}/snapshots`,
    payload,
  );
  return data;
}

/** GET /packages/workspaces/:id/snapshots — List all data snapshots for a workspace. */
export async function listSnapshots(workspaceId: number): Promise<DataSnapshot[]> {
  const { data } = await api.get<DataSnapshot[]>(
    `/packages/workspaces/${workspaceId}/snapshots`,
  );
  return data;
}

/** DELETE /packages/workspaces/:id — Permanently delete a workspace and its nodes. */
export async function deleteWorkspace(workspaceId: number): Promise<void> {
  await api.delete(`/packages/workspaces/${workspaceId}`);
}

/** POST /packages/workspaces/:id/nodes/reorder — Move a node to a new parent or position. */
export async function reorderNode(
  workspaceId: number,
  payload: ReorderNodePayload,
): Promise<PackageWorkspace> {
  const { data } = await api.post<PackageWorkspace>(
    `/packages/workspaces/${workspaceId}/nodes/reorder`,
    payload,
  );
  return data;
}
