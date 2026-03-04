'use client';

import { useEffect, useMemo, useState } from 'react';
import { Download, Loader2, Plus, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { listCourses, type CourseSummary } from '@/lib/course-api';
import {
  addNode,
  buildWorkspace,
  createWorkspace,
  deleteNode,
  downloadArtifact,
  getWorkspace,
  type DatasetBinding,
  type PackageNode,
  type PackageWorkspace,
  type ValidationResult,
  updateNode,
  updateWorkspace,
  validateWorkspace,
  type WorkspaceStatus,
  type BuildJob,
} from '@/lib/package-api';

type PackageWorkspaceConsoleProps = {
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
};

const DATASET_BINDINGS: Array<{ value: DatasetBinding; label: string }> = [
  { value: 'ROSTER', label: 'Roster CSV' },
  { value: 'COURSE_SUBMISSIONS', label: 'Course Submissions CSV' },
  { value: 'CROSS_COURSE_SUBMISSIONS', label: 'Cross-Course Submissions CSV' },
];

type NodeFormState = {
  label: string;
  nodeType: 'FOLDER' | 'FILE';
  parentId: string;
  orderIndex: string;
  datasetBinding: string;
  bindingCourseId: string;
  identifiable: boolean;
  includeAnswers: boolean;
  filtersText: string;
};

const EMPTY_NODE_FORM: NodeFormState = {
  label: '',
  nodeType: 'FILE',
  parentId: 'ROOT',
  orderIndex: '0',
  datasetBinding: 'ROSTER',
  bindingCourseId: '',
  identifiable: false,
  includeAnswers: false,
  filtersText: '{}',
};

function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function parseFilters(raw: string): Record<string, unknown> | null {
  const trimmed = raw.trim();
  if (!trimmed || trimmed === '{}') return null;
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('Filters must be a JSON object.');
  }
  return parsed as Record<string, unknown>;
}

export default function PackageWorkspaceConsole({ role }: PackageWorkspaceConsoleProps) {
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [coursesLoaded, setCoursesLoaded] = useState(false);

  const [workspace, setWorkspace] = useState<PackageWorkspace | null>(null);
  const [workspaceIdInput, setWorkspaceIdInput] = useState('');

  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createScopeCourseId, setCreateScopeCourseId] = useState('');

  const [workspaceName, setWorkspaceName] = useState('');
  const [workspaceDescription, setWorkspaceDescription] = useState('');
  const [workspaceStatus, setWorkspaceStatus] = useState<WorkspaceStatus>('DRAFT');

  const [addNodeForm, setAddNodeForm] = useState<NodeFormState>(EMPTY_NODE_FORM);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [editNodeForm, setEditNodeForm] = useState<NodeFormState>(EMPTY_NODE_FORM);

  const [strictMode, setStrictMode] = useState(true);
  const [snapshotIdText, setSnapshotIdText] = useState('');
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [buildResult, setBuildResult] = useState<BuildJob | null>(null);

  const [isLoadingWorkspace, setIsLoadingWorkspace] = useState(false);
  const [isSavingWorkspace, setIsSavingWorkspace] = useState(false);
  const [isAddingNode, setIsAddingNode] = useState(false);
  const [isSavingNode, setIsSavingNode] = useState(false);
  const [isRunningValidation, setIsRunningValidation] = useState(false);
  const [isRunningBuild, setIsRunningBuild] = useState(false);
  const [isDownloadingArtifact, setIsDownloadingArtifact] = useState(false);

  const folderNodes = useMemo(
    () => (workspace?.nodes ?? []).filter((node) => node.nodeType === 'FOLDER'),
    [workspace],
  );

  const selectedNode = useMemo(
    () => workspace?.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [selectedNodeId, workspace],
  );

  useEffect(() => {
    void ensureCoursesLoaded().catch(() => {
      toast.error('Failed to load courses for workspace builder.');
    });
  }, []);

  async function ensureCoursesLoaded() {
    if (coursesLoaded) return;
    const courseList = await listCourses();
    setCourses(courseList);
    setCoursesLoaded(true);
  }

  function seedWorkspaceFields(next: PackageWorkspace) {
    setWorkspace(next);
    setWorkspaceIdInput(String(next.id));
    setWorkspaceName(next.name);
    setWorkspaceDescription(next.description);
    setWorkspaceStatus(next.status);
    setSelectedNodeId(null);
    setEditNodeForm(EMPTY_NODE_FORM);
  }

  async function refreshWorkspace(nextId?: number) {
    const id = nextId ?? workspace?.id;
    if (!id) return;
    setIsLoadingWorkspace(true);
    try {
      await ensureCoursesLoaded();
      const fresh = await getWorkspace(id);
      seedWorkspaceFields(fresh);
      setValidationResult(null);
      setBuildResult(null);
    } catch (error) {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to load workspace.');
    } finally {
      setIsLoadingWorkspace(false);
    }
  }

  async function handleCreateWorkspace() {
    if (!createName.trim()) {
      toast.error('Workspace name is required.');
      return;
    }
    setIsLoadingWorkspace(true);
    try {
      await ensureCoursesLoaded();
      const created = await createWorkspace({
        name: createName.trim(),
        description: createDescription.trim() || undefined,
        scopeCourseId: createScopeCourseId ? Number(createScopeCourseId) : undefined,
      });
      seedWorkspaceFields(created);
      setCreateName('');
      setCreateDescription('');
      setCreateScopeCourseId('');
      toast.success('Workspace created.');
    } catch (error) {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to create workspace.');
    } finally {
      setIsLoadingWorkspace(false);
    }
  }

  async function handleOpenWorkspace() {
    const id = Number(workspaceIdInput);
    if (!Number.isFinite(id) || id <= 0) {
      toast.error('Enter a valid workspace ID.');
      return;
    }
    await refreshWorkspace(id);
  }

  async function handleSaveWorkspace() {
    if (!workspace) return;
    setIsSavingWorkspace(true);
    try {
      const updated = await updateWorkspace(workspace.id, {
        name: workspaceName.trim() || workspace.name,
        description: workspaceDescription,
        status: workspaceStatus,
      });
      seedWorkspaceFields(updated);
      toast.success('Workspace updated.');
    } catch (error) {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to update workspace.');
    } finally {
      setIsSavingWorkspace(false);
    }
  }

  async function handleAddNode() {
    if (!workspace) return;
    if (!addNodeForm.label.trim()) {
      toast.error('Node label is required.');
      return;
    }

    setIsAddingNode(true);
    try {
      const filters = addNodeForm.nodeType === 'FILE' ? parseFilters(addNodeForm.filtersText) : null;
      await addNode(workspace.id, {
        parentId: addNodeForm.parentId === 'ROOT' ? null : Number(addNodeForm.parentId),
        nodeType: addNodeForm.nodeType,
        label: addNodeForm.label.trim(),
        orderIndex: Number(addNodeForm.orderIndex) || 0,
        datasetBinding:
          addNodeForm.nodeType === 'FILE' ? (addNodeForm.datasetBinding as DatasetBinding) : null,
        bindingCourseId:
          addNodeForm.nodeType === 'FILE' && addNodeForm.bindingCourseId
            ? Number(addNodeForm.bindingCourseId)
            : null,
        filters,
        identifiable: addNodeForm.nodeType === 'FILE' ? addNodeForm.identifiable : false,
        includeAnswers: addNodeForm.nodeType === 'FILE' ? addNodeForm.includeAnswers : false,
      });
      await refreshWorkspace();
      setAddNodeForm({
        ...EMPTY_NODE_FORM,
        parentId: addNodeForm.parentId,
      });
      toast.success('Node added.');
    } catch (error) {
      const fallback = error instanceof Error ? error.message : 'Failed to add node.';
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback);
    } finally {
      setIsAddingNode(false);
    }
  }

  function startEditNode(node: PackageNode) {
    setSelectedNodeId(node.id);
    setEditNodeForm({
      label: node.label,
      nodeType: node.nodeType,
      parentId: node.parentId == null ? 'ROOT' : String(node.parentId),
      orderIndex: String(node.orderIndex),
      datasetBinding: node.datasetBinding ?? 'ROSTER',
      bindingCourseId: node.bindingCourseId == null ? '' : String(node.bindingCourseId),
      identifiable: Boolean(node.identifiable),
      includeAnswers: Boolean(node.includeAnswers),
      filtersText: node.filters ? JSON.stringify(node.filters, null, 2) : '{}',
    });
  }

  async function handleSaveNode() {
    if (!workspace || !selectedNodeId) return;
    if (!editNodeForm.label.trim()) {
      toast.error('Node label is required.');
      return;
    }
    setIsSavingNode(true);
    try {
      const filters = editNodeForm.nodeType === 'FILE' ? parseFilters(editNodeForm.filtersText) : null;
      await updateNode(workspace.id, selectedNodeId, {
        label: editNodeForm.label.trim(),
        parentId: editNodeForm.parentId === 'ROOT' ? null : Number(editNodeForm.parentId),
        orderIndex: Number(editNodeForm.orderIndex) || 0,
        datasetBinding:
          editNodeForm.nodeType === 'FILE' ? (editNodeForm.datasetBinding as DatasetBinding) : null,
        bindingCourseId:
          editNodeForm.nodeType === 'FILE' && editNodeForm.bindingCourseId
            ? Number(editNodeForm.bindingCourseId)
            : null,
        filters,
        identifiable: editNodeForm.nodeType === 'FILE' ? editNodeForm.identifiable : false,
        includeAnswers: editNodeForm.nodeType === 'FILE' ? editNodeForm.includeAnswers : false,
      });
      await refreshWorkspace();
      toast.success('Node updated.');
    } catch (error) {
      const fallback = error instanceof Error ? error.message : 'Failed to update node.';
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback);
    } finally {
      setIsSavingNode(false);
    }
  }

  async function handleDeleteNode(nodeId: number) {
    if (!workspace) return;
    setIsSavingNode(true);
    try {
      await deleteNode(workspace.id, nodeId);
      await refreshWorkspace();
      if (selectedNodeId === nodeId) {
        setSelectedNodeId(null);
      }
      toast.success('Node deleted.');
    } catch (error) {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to delete node.');
    } finally {
      setIsSavingNode(false);
    }
  }

  async function handleValidateWorkspace() {
    if (!workspace) return;
    setIsRunningValidation(true);
    try {
      const result = await validateWorkspace(workspace.id, {
        strictMode,
        snapshotId: snapshotIdText ? Number(snapshotIdText) : undefined,
      });
      setValidationResult(result);
      if (result.valid) {
        toast.success('Workspace is valid.');
      } else {
        toast.error('Validation failed.');
      }
    } catch (error) {
      const responseData = (error as { response?: { data?: ValidationResult & { detail?: string } } })
        ?.response?.data;
      if (responseData && typeof responseData === 'object' && 'valid' in responseData) {
        setValidationResult(responseData);
      }
      toast.error(responseData?.detail ?? 'Validation failed.');
    } finally {
      setIsRunningValidation(false);
    }
  }

  async function handleBuildWorkspace() {
    if (!workspace) return;
    setIsRunningBuild(true);
    try {
      const job = await buildWorkspace(workspace.id, {
        strictMode,
        snapshotId: snapshotIdText ? Number(snapshotIdText) : undefined,
      });
      setBuildResult(job);
      if (job.status === 'COMPLETED') {
        toast.success('Package build completed.');
      } else {
        toast.error(job.errorMessage ?? 'Package build failed.');
      }
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? 'Package build failed.');
    } finally {
      setIsRunningBuild(false);
    }
  }

  async function handleDownloadArtifact() {
    if (!buildResult?.artifactId) return;
    setIsDownloadingArtifact(true);
    try {
      const { blob, filename } = await downloadArtifact(buildResult.artifactId);
      triggerBrowserDownload(blob, filename);
      toast.success('Artifact download started.');
    } catch (error) {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Download failed.');
    } finally {
      setIsDownloadingArtifact(false);
    }
  }

  return (
    <div className="space-y-6 p-6 w-full max-w-7xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Package Workspaces</h1>
        <p className="text-muted-foreground mt-1">
          Build zipped export packages from a virtual file tree. Role: {role}.
        </p>
      </div>

      <section className="rounded-sm border border-border bg-card p-4 space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Open Or Create Workspace</h2>
        <div className="grid gap-3 md:grid-cols-4">
          <div className="space-y-1 md:col-span-2">
            <Label>Open Workspace ID</Label>
            <div className="flex gap-2">
              <Input
                value={workspaceIdInput}
                onChange={(event) => setWorkspaceIdInput(event.target.value)}
                placeholder="Workspace ID"
              />
              <Button type="button" onClick={() => void handleOpenWorkspace()} disabled={isLoadingWorkspace}>
                {isLoadingWorkspace ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              </Button>
            </div>
          </div>
          <div className="space-y-1">
            <Label>New Workspace Name</Label>
            <Input
              value={createName}
              onChange={(event) => setCreateName(event.target.value)}
              placeholder="Research Export Package"
            />
          </div>
          <div className="space-y-1">
            <Label>Scope Course (optional)</Label>
            <Select value={createScopeCourseId} onValueChange={setCreateScopeCourseId}>
              <SelectTrigger>
                <SelectValue placeholder="Unscoped" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Unscoped</SelectItem>
                {courses.map((course) => (
                  <SelectItem key={course.id} value={String(course.id)}>
                    {course.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1 md:col-span-3">
            <Label>Description</Label>
            <Input
              value={createDescription}
              onChange={(event) => setCreateDescription(event.target.value)}
              placeholder="Optional workspace description"
            />
          </div>
          <div className="flex items-end">
            <Button type="button" onClick={() => void handleCreateWorkspace()} disabled={isLoadingWorkspace}>
              <Plus className="mr-2 h-4 w-4" />
              Create Workspace
            </Button>
          </div>
        </div>
      </section>

      {!workspace ? (
        <div className="rounded-sm border border-border bg-card p-8 text-center text-sm text-muted-foreground">
          Open an existing workspace ID or create a new one to start building a package.
        </div>
      ) : (
        <>
          <section className="rounded-sm border border-border bg-card p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">
                Workspace #{workspace.id} (Revision {workspace.revision})
              </h2>
              <p className="text-xs text-muted-foreground">
                Updated {new Date(workspace.updatedAt).toLocaleString()}
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-1">
                <Label>Name</Label>
                <Input value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} />
              </div>
              <div className="space-y-1">
                <Label>Status</Label>
                <Select
                  value={workspaceStatus}
                  onValueChange={(value) => setWorkspaceStatus(value as WorkspaceStatus)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DRAFT">DRAFT</SelectItem>
                    <SelectItem value="SEALED">SEALED</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>Scope Course ID</Label>
                <Input value={workspace.scopeCourseId ?? ''} readOnly />
              </div>
              <div className="space-y-1 md:col-span-3">
                <Label>Description</Label>
                <Input
                  value={workspaceDescription}
                  onChange={(event) => setWorkspaceDescription(event.target.value)}
                />
              </div>
            </div>

            <div className="flex gap-2">
              <Button type="button" onClick={() => void handleSaveWorkspace()} disabled={isSavingWorkspace}>
                {isSavingWorkspace ? 'Saving...' : 'Save Workspace'}
              </Button>
              <Button type="button" variant="outline" onClick={() => void refreshWorkspace()} disabled={isLoadingWorkspace}>
                Refresh
              </Button>
            </div>
          </section>

          <section className="rounded-sm border border-border bg-card p-4 space-y-4">
            <h2 className="text-lg font-semibold text-foreground">Add Node</h2>
            <div className="grid gap-3 md:grid-cols-4">
              <div className="space-y-1">
                <Label>Label</Label>
                <Input
                  value={addNodeForm.label}
                  onChange={(event) => setAddNodeForm((prev) => ({ ...prev, label: event.target.value }))}
                />
              </div>
              <div className="space-y-1">
                <Label>Node Type</Label>
                <Select
                  value={addNodeForm.nodeType}
                  onValueChange={(value) =>
                    setAddNodeForm((prev) => ({
                      ...prev,
                      nodeType: value as 'FOLDER' | 'FILE',
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="FOLDER">FOLDER</SelectItem>
                    <SelectItem value="FILE">FILE</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>Parent</Label>
                <Select
                  value={addNodeForm.parentId}
                  onValueChange={(value) => setAddNodeForm((prev) => ({ ...prev, parentId: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ROOT">Root</SelectItem>
                    {folderNodes.map((node) => (
                      <SelectItem key={node.id} value={String(node.id)}>
                        {node.label} (#{node.id})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>Order Index</Label>
                <Input
                  value={addNodeForm.orderIndex}
                  onChange={(event) =>
                    setAddNodeForm((prev) => ({ ...prev, orderIndex: event.target.value }))
                  }
                />
              </div>
            </div>

            {addNodeForm.nodeType === 'FILE' && (
              <div className="grid gap-3 md:grid-cols-3">
                <div className="space-y-1">
                  <Label>Dataset Binding</Label>
                  <Select
                    value={addNodeForm.datasetBinding}
                    onValueChange={(value) =>
                      setAddNodeForm((prev) => ({ ...prev, datasetBinding: value }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {DATASET_BINDINGS.map((binding) => (
                        <SelectItem key={binding.value} value={binding.value}>
                          {binding.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label>Binding Course ID (optional)</Label>
                  <Input
                    value={addNodeForm.bindingCourseId}
                    onChange={(event) =>
                      setAddNodeForm((prev) => ({ ...prev, bindingCourseId: event.target.value }))
                    }
                    placeholder="e.g. 12"
                  />
                </div>
                <div className="space-y-1">
                  <Label>Filters JSON (optional)</Label>
                  <Input
                    value={addNodeForm.filtersText}
                    onChange={(event) =>
                      setAddNodeForm((prev) => ({ ...prev, filtersText: event.target.value }))
                    }
                    placeholder='{"status":"SUBMITTED"}'
                  />
                </div>
                <div className="md:col-span-3 flex gap-6">
                  <label className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Checkbox
                      checked={addNodeForm.identifiable}
                      onCheckedChange={(checked) =>
                        setAddNodeForm((prev) => ({ ...prev, identifiable: checked === true }))
                      }
                    />
                    Identifiable output
                  </label>
                  <label className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Checkbox
                      checked={addNodeForm.includeAnswers}
                      onCheckedChange={(checked) =>
                        setAddNodeForm((prev) => ({ ...prev, includeAnswers: checked === true }))
                      }
                    />
                    Include answer details
                  </label>
                </div>
              </div>
            )}

            <Button type="button" onClick={() => void handleAddNode()} disabled={isAddingNode}>
              {isAddingNode ? 'Adding...' : 'Add Node'}
            </Button>
          </section>

          <section className="rounded-sm border border-border bg-card overflow-hidden">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="text-lg font-semibold text-foreground">Workspace Nodes</h2>
            </div>
            <Table>
              <TableHeader>
                <TableRow className="bg-muted border-b border-border">
                  <TableHead>ID</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Label</TableHead>
                  <TableHead>Parent</TableHead>
                  <TableHead>Binding</TableHead>
                  <TableHead>Course</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {workspace.nodes.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                      No nodes yet.
                    </TableCell>
                  </TableRow>
                )}
                {workspace.nodes.map((node) => (
                  <TableRow
                    key={node.id}
                    className={selectedNodeId === node.id ? 'bg-accent/60' : 'even:bg-muted/40'}
                  >
                    <TableCell>{node.id}</TableCell>
                    <TableCell>{node.nodeType}</TableCell>
                    <TableCell className="font-medium">{node.label}</TableCell>
                    <TableCell>{node.parentId ?? '-'}</TableCell>
                    <TableCell>{node.datasetBinding ?? '-'}</TableCell>
                    <TableCell>{node.bindingCourseId ?? '-'}</TableCell>
                    <TableCell className="text-right">
                      <div className="inline-flex gap-2">
                        <Button type="button" size="sm" variant="outline" onClick={() => startEditNode(node)}>
                          Edit
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="destructive"
                          onClick={() => void handleDeleteNode(node.id)}
                          disabled={isSavingNode}
                        >
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </section>

          {selectedNode && (
            <section className="rounded-sm border border-border bg-card p-4 space-y-4">
              <h2 className="text-lg font-semibold text-foreground">
                Edit Node #{selectedNode.id}
              </h2>
              <div className="grid gap-3 md:grid-cols-4">
                <div className="space-y-1">
                  <Label>Label</Label>
                  <Input
                    value={editNodeForm.label}
                    onChange={(event) => setEditNodeForm((prev) => ({ ...prev, label: event.target.value }))}
                  />
                </div>
                <div className="space-y-1">
                  <Label>Parent</Label>
                  <Select
                    value={editNodeForm.parentId}
                    onValueChange={(value) => setEditNodeForm((prev) => ({ ...prev, parentId: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ROOT">Root</SelectItem>
                      {folderNodes
                        .filter((node) => node.id !== selectedNode.id)
                        .map((node) => (
                          <SelectItem key={node.id} value={String(node.id)}>
                            {node.label} (#{node.id})
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label>Order Index</Label>
                  <Input
                    value={editNodeForm.orderIndex}
                    onChange={(event) =>
                      setEditNodeForm((prev) => ({ ...prev, orderIndex: event.target.value }))
                    }
                  />
                </div>
                <div className="space-y-1">
                  <Label>Node Type</Label>
                  <Input value={editNodeForm.nodeType} readOnly />
                </div>
              </div>

              {editNodeForm.nodeType === 'FILE' && (
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="space-y-1">
                    <Label>Dataset Binding</Label>
                    <Select
                      value={editNodeForm.datasetBinding}
                      onValueChange={(value) =>
                        setEditNodeForm((prev) => ({ ...prev, datasetBinding: value }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {DATASET_BINDINGS.map((binding) => (
                          <SelectItem key={binding.value} value={binding.value}>
                            {binding.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label>Binding Course ID</Label>
                    <Input
                      value={editNodeForm.bindingCourseId}
                      onChange={(event) =>
                        setEditNodeForm((prev) => ({ ...prev, bindingCourseId: event.target.value }))
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Filters JSON</Label>
                    <Input
                      value={editNodeForm.filtersText}
                      onChange={(event) =>
                        setEditNodeForm((prev) => ({ ...prev, filtersText: event.target.value }))
                      }
                    />
                  </div>
                  <div className="md:col-span-3 flex gap-6">
                    <label className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Checkbox
                        checked={editNodeForm.identifiable}
                        onCheckedChange={(checked) =>
                          setEditNodeForm((prev) => ({ ...prev, identifiable: checked === true }))
                        }
                      />
                      Identifiable output
                    </label>
                    <label className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Checkbox
                        checked={editNodeForm.includeAnswers}
                        onCheckedChange={(checked) =>
                          setEditNodeForm((prev) => ({ ...prev, includeAnswers: checked === true }))
                        }
                      />
                      Include answer details
                    </label>
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <Button type="button" onClick={() => void handleSaveNode()} disabled={isSavingNode}>
                  {isSavingNode ? 'Saving...' : 'Save Node'}
                </Button>
                <Button type="button" variant="outline" onClick={() => setSelectedNodeId(null)}>
                  Cancel
                </Button>
              </div>
            </section>
          )}

          <section className="rounded-sm border border-border bg-card p-4 space-y-4">
            <h2 className="text-lg font-semibold text-foreground">Validate & Build</h2>
            <div className="grid gap-3 md:grid-cols-3">
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <Checkbox checked={strictMode} onCheckedChange={(checked) => setStrictMode(checked === true)} />
                Strict mode
              </label>
              <div className="space-y-1">
                <Label>Snapshot ID (optional)</Label>
                <Input
                  value={snapshotIdText}
                  onChange={(event) => setSnapshotIdText(event.target.value)}
                  placeholder="Live mode if blank"
                />
              </div>
            </div>

            <div className="flex gap-2 flex-wrap">
              <Button type="button" onClick={() => void handleValidateWorkspace()} disabled={isRunningValidation}>
                {isRunningValidation ? 'Validating...' : 'Validate Workspace'}
              </Button>
              <Button type="button" variant="outline" onClick={() => void handleBuildWorkspace()} disabled={isRunningBuild}>
                {isRunningBuild ? 'Building...' : 'Build Package'}
              </Button>
              {buildResult?.artifactId && buildResult.status === 'COMPLETED' && (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => void handleDownloadArtifact()}
                  disabled={isDownloadingArtifact}
                >
                  <Download className="mr-2 h-4 w-4" />
                  {isDownloadingArtifact ? 'Downloading...' : 'Download Artifact'}
                </Button>
              )}
            </div>

            {validationResult && (
              <div className="rounded-sm border border-border p-3 text-sm space-y-2">
                <p className="font-medium text-foreground">
                  Validation: {validationResult.valid ? 'VALID' : 'INVALID'} | Files: {validationResult.fileCount} | Estimated rows: {validationResult.estimatedRows}
                </p>
                {validationResult.violations.length > 0 && (
                  <div>
                    <p className="font-medium text-destructive mb-1">Violations</p>
                    <ul className="list-disc pl-5 text-muted-foreground space-y-1">
                      {validationResult.violations.map((issue, index) => (
                        <li key={`${issue.code}-${index}`}>
                          [{issue.code}] {issue.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {validationResult.warnings.length > 0 && (
                  <div>
                    <p className="font-medium text-amber-600 mb-1">Warnings</p>
                    <ul className="list-disc pl-5 text-muted-foreground space-y-1">
                      {validationResult.warnings.map((issue, index) => (
                        <li key={`${issue.code}-${index}`}>
                          [{issue.code}] {issue.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {buildResult && (
              <div className="rounded-sm border border-border p-3 text-sm">
                <p className="font-medium text-foreground">
                  Build #{buildResult.id}: {buildResult.status}
                </p>
                {buildResult.errorMessage && (
                  <p className="text-destructive mt-1">{buildResult.errorMessage}</p>
                )}
                {buildResult.warnings && buildResult.warnings.length > 0 && (
                  <p className="text-muted-foreground mt-1">
                    {buildResult.warnings.length} warning(s) emitted during build.
                  </p>
                )}
                {buildResult.artifactId && (
                  <p className="text-muted-foreground mt-1">Artifact ID: {buildResult.artifactId}</p>
                )}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
