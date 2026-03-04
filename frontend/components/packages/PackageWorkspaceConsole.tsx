'use client';

import { useEffect, useMemo, useState } from 'react';
import { ChevronRight, ChevronDown, Download, Folder, File, Plus, RefreshCw, Save, X } from 'lucide-react';
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
  canExportIdentifiable: boolean;
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

function sortByOrder(nodes: PackageNode[]) {
  return [...nodes].sort((a, b) => {
    if (a.orderIndex !== b.orderIndex) {
      return a.orderIndex - b.orderIndex;
    }
    return a.id - b.id;
  });
}

function getSiblings(nodes: PackageNode[], node: PackageNode) {
  return sortByOrder(nodes.filter((candidate) => candidate.parentId === node.parentId));
}

function prettyLabel(node: PackageNode) {
  return `${node.label}${node.nodeType === 'FOLDER' ? '/' : ''}`;
}

function buildWorkspaceTree(nodes: PackageNode[]) {
  const byParent = new Map<string, PackageNode[]>();
  for (const node of sortByOrder(nodes)) {
    const key = node.parentId == null ? 'ROOT' : String(node.parentId);
    const bucket = byParent.get(key) ?? [];
    bucket.push(node);
    byParent.set(key, bucket);
  }
  return byParent;
}

function formatNodeDescription(node: PackageNode) {
  if (node.nodeType === 'FOLDER') return 'Folder';
  const binding = node.datasetBinding ?? 'No dataset';
  const course = node.bindingCourseId == null ? 'all' : `course ${node.bindingCourseId}`;
  return `${binding} · ${course}`;
}

export default function PackageWorkspaceConsole({
  role,
  canExportIdentifiable,
}: PackageWorkspaceConsoleProps) {
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

  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());
  const [addQuickMode, setAddQuickMode] = useState<'FOLDER' | 'FILE'>('FILE');
  const [newNodeLabel, setNewNodeLabel] = useState('');

  const [editNodeForm, setEditNodeForm] = useState<NodeFormState>(EMPTY_NODE_FORM);

  const [strictMode, setStrictMode] = useState(true);
  const [snapshotIdText, setSnapshotIdText] = useState('');
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [buildResult, setBuildResult] = useState<BuildJob | null>(null);

  const [isLoadingWorkspace, setIsLoadingWorkspace] = useState(false);
  const [isSavingWorkspace, setIsSavingWorkspace] = useState(false);
  const [isAddingNode, setIsAddingNode] = useState(false);
  const [isSavingNode, setIsSavingNode] = useState(false);
  const [isDeletingNode, setIsDeletingNode] = useState(false);
  const [isRunningValidation, setIsRunningValidation] = useState(false);
  const [isRunningBuild, setIsRunningBuild] = useState(false);
  const [isDownloadingArtifact, setIsDownloadingArtifact] = useState(false);

  const treeMap = useMemo(() => buildWorkspaceTree(workspace?.nodes ?? []), [workspace?.nodes]);

  const selectedNode = useMemo(
    () => workspace?.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [selectedNodeId, workspace?.nodes],
  );

  const hasSelectedFolder = selectedNode?.nodeType === 'FOLDER';
  const selectedParentLabel = selectedNode?.parentId == null ? 'Root' : `#${selectedNode.parentId}`;
  const siblingNodes = useMemo(() => {
    if (!selectedNode) return [];
    return getSiblings(workspace?.nodes ?? [], selectedNode);
  }, [selectedNode, workspace?.nodes]);

  useEffect(() => {
    void ensureCoursesLoaded();
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
    setValidationResult(null);
    setBuildResult(null);
    setAddQuickMode('FILE');
    setNewNodeLabel('');
  }

  async function refreshWorkspace(nextId?: number) {
    const id = nextId ?? workspace?.id;
    if (!id) return;
    setIsLoadingWorkspace(true);
    try {
      await ensureCoursesLoaded();
      const fresh = await getWorkspace(id);
      seedWorkspaceFields(fresh);
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

  async function moveSelectedNode(direction: 'up' | 'down') {
    if (!workspace || !selectedNode) return;
    const siblingNodes = getSiblings(workspace.nodes, selectedNode);
    const index = siblingNodes.findIndex((node) => node.id === selectedNode.id);
    const swapWith = direction === 'up' ? index - 1 : index + 1;
    if (swapWith < 0 || swapWith >= siblingNodes.length) return;

    const current = siblingNodes[index];
    const target = siblingNodes[swapWith];

    setIsSavingNode(true);
    try {
      await updateNode(workspace.id, current.id, {
        parentId: current.parentId,
        orderIndex: target.orderIndex,
      });
      await updateNode(workspace.id, target.id, {
        parentId: target.parentId,
        orderIndex: current.orderIndex,
      });
      await refreshWorkspace();
      setSelectedNodeId(current.id);
      toast.success('Order updated.');
    } catch (error) {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to move node.');
    } finally {
      setIsSavingNode(false);
    }
  }

  async function handleAddNode() {
    if (!workspace) return;
    if (!newNodeLabel.trim()) {
      toast.error('Node label is required.');
      return;
    }

    setIsAddingNode(true);
    try {
      await addNode(workspace.id, {
        parentId: selectedNodeId == null ? null : selectedNode?.nodeType === 'FOLDER' ? selectedNodeId : selectedNode?.parentId,
        nodeType: addQuickMode,
        label: newNodeLabel.trim(),
        orderIndex: workspace.nodes.filter((node) => node.parentId === (selectedNode?.nodeType === 'FOLDER' ? selectedNodeId : null)).length,
        datasetBinding: addQuickMode === 'FILE' ? 'ROSTER' : null,
        bindingCourseId: null,
        filters: null,
        identifiable: false,
        includeAnswers: false,
      });
      await refreshWorkspace();
      setNewNodeLabel('');
      toast.success('Node added.');
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? 'Failed to add node.');
    } finally {
      setIsAddingNode(false);
    }
  }

  async function handleSelectNode(node: PackageNode) {
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
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      next.add(node.id);
      return next;
    });
  }

  async function handleSaveNode() {
    if (!workspace || !selectedNode) return;
    setIsSavingNode(true);
    try {
      const filters =
        editNodeForm.nodeType === 'FILE' ? parseFilters(editNodeForm.filtersText) : null;
      const payload = {
        label: editNodeForm.label.trim() || selectedNode.label,
        parentId: editNodeForm.parentId === 'ROOT' ? null : Number(editNodeForm.parentId),
        orderIndex: Number(editNodeForm.orderIndex) || 0,
        datasetBinding:
          editNodeForm.nodeType === 'FILE'
            ? (editNodeForm.datasetBinding as DatasetBinding)
            : null,
        bindingCourseId:
          editNodeForm.nodeType === 'FILE' && editNodeForm.bindingCourseId
            ? Number(editNodeForm.bindingCourseId)
            : null,
        filters,
        identifiable:
          editNodeForm.nodeType === 'FILE' ? editNodeForm.identifiable : false,
        includeAnswers:
          editNodeForm.nodeType === 'FILE' ? editNodeForm.includeAnswers : false,
      };
      await updateNode(workspace.id, selectedNode.id, payload);
      await refreshWorkspace();
      toast.success('Node updated.');
    } catch (error) {
      const fallback = error instanceof Error ? error.message : 'Failed to update node.';
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback);
    } finally {
      setIsSavingNode(false);
    }
  }

  async function handleDeleteNode() {
    if (!workspace || !selectedNode) return;
    setIsDeletingNode(true);
    try {
      await deleteNode(workspace.id, selectedNode.id);
      await refreshWorkspace();
      setSelectedNodeId(null);
      toast.success('Node deleted.');
    } catch (error) {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to delete node.');
    } finally {
      setIsDeletingNode(false);
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
      const responseData =
        (error as { response?: { data?: ValidationResult & { detail?: string } } })?.response?.data;
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

  function renderNode(node: PackageNode, depth: number) {
    const children = treeMap.get(String(node.id)) ?? [];
    const isExpanded = expandedNodes.has(node.id);
    const hasChildren = children.length > 0;

    return (
      <div key={node.id} className="space-y-1">
        <div
          className={`group flex min-h-9 cursor-pointer items-center gap-2 rounded-sm px-2 py-1 text-sm ${
            selectedNodeId === node.id ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/40'
          }`}
          style={{ paddingLeft: `${depth * 14 + 4}px` }}
          onClick={() => void handleSelectNode(node)}
          role="button"
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown
                className="h-4 w-4 text-muted-foreground"
                onClick={(event) => {
                  event.stopPropagation();
                  setExpandedNodes((prev) => {
                    const next = new Set(prev);
                    next.delete(node.id);
                    return next;
                  });
                }}
              />
            ) : (
              <ChevronRight
                className="h-4 w-4 text-muted-foreground"
                onClick={(event) => {
                  event.stopPropagation();
                  setExpandedNodes((prev) => new Set(prev).add(node.id));
                }}
              />
            )
          ) : (
            <span className="inline-block h-4 w-4" />
          )}
          {node.nodeType === 'FOLDER' ? (
            <Folder className="h-4 w-4 text-amber-500" />
          ) : (
            <File className="h-4 w-4 text-sky-500" />
          )}
          <span className="truncate font-medium text-foreground">{prettyLabel(node)}</span>
          <span className="ml-auto text-xs text-muted-foreground">#{node.id}</span>
        </div>
        {hasChildren && isExpanded
          ? children.map((child) => renderNode(child, depth + 1))
          : null}
      </div>
    );
  }

  const rootNodes = treeMap.get('ROOT') ?? [];

  return (
    <div className="w-full max-w-7xl space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Package Workspaces</h1>
        <p className="text-muted-foreground mt-1">Build export packages with a file-style tree interface.</p>
      </div>

      <section className="rounded-sm border border-border bg-card p-4 space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Open or create a workspace</h2>
        <div className="grid gap-3 md:grid-cols-5">
          <div className="space-y-1 md:col-span-2">
            <Label>Open Workspace ID</Label>
            <div className="flex gap-2">
              <Input
                value={workspaceIdInput}
                onChange={(event) => setWorkspaceIdInput(event.target.value)}
                placeholder="Workspace ID"
              />
              <Button type="button" onClick={() => void handleOpenWorkspace()} disabled={isLoadingWorkspace}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Open
              </Button>
            </div>
          </div>
          <div className="space-y-1">
            <Label>New Workspace Name</Label>
            <Input
              value={createName}
              onChange={(event) => setCreateName(event.target.value)}
              placeholder="Export Package"
            />
          </div>
          <div className="space-y-1">
            <Label>Scope Course (optional)</Label>
            <Select
              value={createScopeCourseId || '__NONE__'}
              onValueChange={(value) => setCreateScopeCourseId(value === '__NONE__' ? '' : value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Unscoped" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__NONE__">Unscoped</SelectItem>
                {courses.map((course) => (
                  <SelectItem key={course.id} value={String(course.id)}>
                    {course.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1 flex items-end">
            <Button type="button" onClick={() => void handleCreateWorkspace()} disabled={isLoadingWorkspace}>
              <Plus className="mr-2 h-4 w-4" />
              Create
            </Button>
          </div>
          <div className="space-y-1 md:col-span-5">
            <Label>Description</Label>
            <Input
              value={createDescription}
              onChange={(event) => setCreateDescription(event.target.value)}
              placeholder="Optional workspace description"
            />
          </div>
        </div>
      </section>

      {!workspace ? (
        <div className="rounded-sm border border-border bg-card p-8 text-center text-sm text-muted-foreground">
          Open an existing workspace or create a new one to start building your package.
        </div>
      ) : (
        <>
          <section className="rounded-sm border border-border bg-card p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">
                Workspace #{workspace.id} · Revision {workspace.revision}
              </h2>
              <p className="text-xs text-muted-foreground">Updated {new Date(workspace.updatedAt).toLocaleString()}</p>
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
                <Label>Scope Course</Label>
                <Input value={workspace.scopeCourseId ?? ''} readOnly />
              </div>
              <div className="md:col-span-3 space-y-1">
                <Label>Description</Label>
                <Input value={workspaceDescription} onChange={(event) => setWorkspaceDescription(event.target.value)} />
              </div>
            </div>

            <div className="flex gap-2">
              <Button type="button" onClick={() => void handleSaveWorkspace()} disabled={isSavingWorkspace}>
                <Save className="mr-2 h-4 w-4" />
                {isSavingWorkspace ? 'Saving...' : 'Save'}
              </Button>
              <Button type="button" variant="outline" onClick={() => void refreshWorkspace()} disabled={isLoadingWorkspace}>
                Refresh
              </Button>
            </div>
          </section>

          <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
            <section className="rounded-sm border border-border bg-card p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-foreground">Tree</h2>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => setExpandedNodes(new Set(rootNodes.map((node) => node.id)))}
                >
                  Expand All
                </Button>
              </div>

              {rootNodes.length === 0 ? (
                <p className="text-sm text-muted-foreground">No nodes yet. Add one below.</p>
              ) : (
                <div className="space-y-1">
                  {rootNodes.map((node) => renderNode(node, 0))}
                </div>
              )}

              <div className="space-y-2 border-t border-border pt-3">
                <p className="text-sm font-medium text-foreground">Add item in {selectedNode ? `#${selectedNodeId} (${selectedNode.label})` : 'root'}</p>
                <div className="grid grid-cols-6 gap-2">
                  <Select value={addQuickMode} onValueChange={(value) => setAddQuickMode(value as 'FOLDER' | 'FILE')}>
                    <SelectTrigger className="col-span-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="FILE">File</SelectItem>
                      <SelectItem value="FOLDER">Folder</SelectItem>
                    </SelectContent>
                  </Select>
                  <Input
                    className="col-span-4"
                    placeholder={`Add ${addQuickMode.toLowerCase()} name`}
                    value={newNodeLabel}
                    onChange={(event) => setNewNodeLabel(event.target.value)}
                  />
                </div>
                <Button
                  type="button"
                  className="w-full"
                  onClick={() => void handleAddNode()}
                  disabled={isAddingNode}
                >
                  {isAddingNode ? 'Adding...' : `Add ${addQuickMode.toLowerCase()}`}
                </Button>
                <p className="text-xs text-muted-foreground">
                  Use folder nodes to create nested structures. Drag-like reordering is handled with
                  Up / Down on the selected item.
                </p>
              </div>
            </section>

            <section className="space-y-4">
              <div className="rounded-sm border border-border bg-card p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-foreground">Selection</h2>
                  <p className="text-sm text-muted-foreground">
                    Parent: {selectedParentLabel}
                  </p>
                </div>

                {!selectedNode ? (
                  <p className="text-sm text-muted-foreground">Select a file or folder in the tree to edit its settings.</p>
                ) : (
                  <div className="space-y-3">
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="space-y-1">
                        <Label>Label</Label>
                        <Input
                          value={editNodeForm.label}
                          onChange={(event) => setEditNodeForm((prev) => ({ ...prev, label: event.target.value }))}
                        />
                      </div>
                      <div className="space-y-1">
                        <Label>Type</Label>
                        <Input value={editNodeForm.nodeType} readOnly />
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
                            {workspace.nodes
                              .filter((candidate) => candidate.id !== selectedNode.id && candidate.nodeType === 'FOLDER')
                              .map((candidate) => (
                                <SelectItem key={candidate.id} value={String(candidate.id)}>
                                  {candidate.label} (#{candidate.id})
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1">
                        <Label>Order</Label>
                        <Input
                          value={editNodeForm.orderIndex}
                          onChange={(event) => setEditNodeForm((prev) => ({ ...prev, orderIndex: event.target.value }))}
                        />
                      </div>
                    </div>

                    <p className="text-sm text-muted-foreground">{formatNodeDescription(selectedNode)}</p>

                    {selectedNode.nodeType === 'FILE' ? (
                      <div className="space-y-3 border border-border p-3 rounded-sm">
                        <div className="grid gap-3 md:grid-cols-2">
                          <div className="space-y-1">
                            <Label>Dataset Binding</Label>
                            <Select
                              value={editNodeForm.datasetBinding}
                              onValueChange={(value) => setEditNodeForm((prev) => ({ ...prev, datasetBinding: value }))}
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
                              onChange={(event) => setEditNodeForm((prev) => ({ ...prev, bindingCourseId: event.target.value }))}
                            />
                          </div>
                          <div className="space-y-1 md:col-span-2">
                            <Label>Filters JSON</Label>
                            <Input
                              value={editNodeForm.filtersText}
                              onChange={(event) => setEditNodeForm((prev) => ({ ...prev, filtersText: event.target.value }))}
                            />
                          </div>
                        </div>
                        <div className="grid gap-3 md:grid-cols-2">
                          <label className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Checkbox
                              checked={editNodeForm.identifiable}
                              disabled={!canExportIdentifiable}
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
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        Folder nodes only control structure. Bindings belong to file nodes.
                      </p>
                    )}

                    <div className="flex flex-wrap gap-2">
                      <Button type="button" onClick={() => void moveSelectedNode('up')} disabled={isSavingNode}>
                        Move Up
                      </Button>
                      <Button type="button" variant="outline" onClick={() => void moveSelectedNode('down')} disabled={isSavingNode}>
                        Move Down
                      </Button>
                      <Button type="button" onClick={() => void handleSaveNode()} disabled={isSavingNode}>
                        <Save className="mr-2 h-4 w-4" />
                        {isSavingNode ? 'Saving...' : 'Save changes'}
                      </Button>
                      <Button type="button" variant="destructive" onClick={() => void handleDeleteNode()} disabled={isDeletingNode}>
                        {isDeletingNode ? 'Deleting...' : 'Delete'}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => {
                          setSelectedNodeId(null);
                          setEditNodeForm(EMPTY_NODE_FORM);
                        }}
                      >
                        <X className="mr-2 h-4 w-4" />
                        Clear
                      </Button>
                    </div>
                    {selectedNode.nodeType === 'FILE' && (
                      <p className="text-xs text-muted-foreground">
                        Sibling count: {siblingNodes.length}. Use up/down to reorder within the same folder.
                      </p>
                    )}
                  </div>
                )}
              </div>

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

                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    onClick={() => void handleValidateWorkspace()}
                    disabled={isRunningValidation}
                  >
                    {isRunningValidation ? 'Validating...' : 'Validate'}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void handleBuildWorkspace()}
                    disabled={isRunningBuild}
                  >
                    {isRunningBuild ? 'Building...' : 'Build'}
                  </Button>
                  {buildResult?.artifactId && buildResult.status === 'COMPLETED' && (
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => void handleDownloadArtifact()}
                      disabled={isDownloadingArtifact}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      {isDownloadingArtifact ? 'Downloading...' : 'Download package'}
                    </Button>
                  )}
                </div>

                {validationResult && (
                  <div className="rounded-sm border border-border p-3 text-sm space-y-2">
                    <p className="font-medium text-foreground">
                      Validation: {validationResult.valid ? 'valid' : 'invalid'} | Files: {validationResult.fileCount} | Estimated rows: {validationResult.estimatedRows}
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
                    {buildResult.errorMessage && <p className="text-destructive mt-1">{buildResult.errorMessage}</p>}
                    {buildResult.warnings && buildResult.warnings.length > 0 && (
                      <p className="text-muted-foreground mt-1">
                        {buildResult.warnings.length} warning(s) emitted during build.
                      </p>
                    )}
                    {buildResult.artifactId && <p className="text-muted-foreground mt-1">Artifact ID: {buildResult.artifactId}</p>}
                  </div>
                )}

                {!canExportIdentifiable && role === 'RESEARCHER' && (
                  <div className="rounded-sm border border-border bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
                    Identifiable nodes are disabled. Request EXPORT_IDENTIFIABLE to unlock.
                  </div>
                )}
              </section>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
