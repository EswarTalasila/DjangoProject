'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Download,
  File,
  FilePlus,
  Folder,
  FolderOpen,
  FolderPlus,
  MoveDown,
  MoveUp,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Trash2,
} from 'lucide-react';
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
  type BuildJob,
  type DatasetBinding,
  type PackageNode,
  type PackageWorkspace,
  type ValidationResult,
  updateNode,
  updateWorkspace,
  validateWorkspace,
  type WorkspaceStatus,
} from '@/lib/package-api';

type PackageWorkspaceConsoleProps = {
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
  canExportIdentifiable: boolean;
};

type AddCursor = { parentId: 'ROOT' | number; kind: 'FOLDER' | 'FILE'; label: string };
type NodeBindingForm = {
  datasetBinding: DatasetBinding;
  bindingCourseId: string;
  identifiable: boolean;
  includeAnswers: boolean;
  filtersText: string;
};

const DATASET_BINDINGS: Array<{ value: DatasetBinding; label: string }> = [
  { value: 'ROSTER', label: 'Roster CSV' },
  { value: 'COURSE_SUBMISSIONS', label: 'Course Submissions CSV' },
  { value: 'CROSS_COURSE_SUBMISSIONS', label: 'Cross-Course Submissions CSV' },
];

const ROOT_SELECT = '__ROOT__';
const ADD_ROOT_ID = '__ADD_ROOT__';

function parseFilters(raw: string): Record<string, unknown> | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('Filters must be a JSON object.');
  }
  return parsed as Record<string, unknown>;
}

function sortNodes(nodes: PackageNode[]) {
  return [...nodes].sort((a, b) => {
    if (a.orderIndex !== b.orderIndex) return a.orderIndex - b.orderIndex;
    return a.id - b.id;
  });
}

function buildChildrenMap(nodes: PackageNode[]) {
  const map = new Map<string, PackageNode[]>();
  for (const node of sortNodes(nodes)) {
    const key = node.parentId == null ? 'ROOT' : String(node.parentId);
    const bucket = map.get(key) ?? [];
    bucket.push(node);
    map.set(key, bucket);
  }
  return map;
}

function toErrorMessage(error: unknown) {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Unexpected error.';
}

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
  const [createScopeCourseId, setCreateScopeCourseId] = useState(ROOT_SELECT);

  const [workspaceName, setWorkspaceName] = useState('');
  const [workspaceDescription, setWorkspaceDescription] = useState('');
  const [workspaceStatus, setWorkspaceStatus] = useState<WorkspaceStatus>('DRAFT');

  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<number>>(new Set());
  const [addCursor, setAddCursor] = useState<AddCursor | null>(null);
  const [editingNodeId, setEditingNodeId] = useState<number | null>(null);
  const [editingLabel, setEditingLabel] = useState('');
  const [nodeLabel, setNodeLabel] = useState('');
  const [nodeOrderIndex, setNodeOrderIndex] = useState('0');
  const [nodeParentId, setNodeParentId] = useState(ROOT_SELECT);
  const [nodeBinding, setNodeBinding] = useState<NodeBindingForm>({
    datasetBinding: 'ROSTER',
    bindingCourseId: ROOT_SELECT,
    identifiable: false,
    includeAnswers: false,
    filtersText: '',
  });

  const [strictMode, setStrictMode] = useState(true);
  const [snapshotIdText, setSnapshotIdText] = useState('');
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [buildResult, setBuildResult] = useState<BuildJob | null>(null);

  const [isLoadingWorkspace, setIsLoadingWorkspace] = useState(false);
  const [isSavingWorkspace, setIsSavingWorkspace] = useState(false);
  const [isSavingNode, setIsSavingNode] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isBuilding, setIsBuilding] = useState(false);
  const [isDownloadingArtifact, setIsDownloadingArtifact] = useState(false);

  const childrenMap = useMemo(() => buildChildrenMap(workspace?.nodes ?? []), [workspace?.nodes]);

  const selectedNode = useMemo(
    () => workspace?.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [workspace?.nodes, selectedNodeId],
  );

  useEffect(() => {
    if (coursesLoaded) return;
    void loadCourses();
  }, [coursesLoaded]);

  async function loadCourses() {
    if (coursesLoaded) return;
    const list = await listCourses();
    setCourses(list);
    setCoursesLoaded(true);
  }

  function seedWorkspace(next: PackageWorkspace) {
    setWorkspace(next);
    setWorkspaceIdInput(String(next.id));
    setWorkspaceName(next.name);
    setWorkspaceDescription(next.description);
    setWorkspaceStatus(next.status);
    setSelectedNodeId(null);
    setEditingNodeId(null);
    setValidationResult(null);
    setBuildResult(null);
    setExpandedFolders(new Set());
    setAddCursor(null);
  }

  function hydrateNodeForm(node: PackageNode | null) {
    if (!node) {
      setNodeLabel('');
      setNodeOrderIndex('0');
      setNodeParentId(ROOT_SELECT);
      setNodeBinding({
        datasetBinding: 'ROSTER',
        bindingCourseId: ROOT_SELECT,
        identifiable: false,
        includeAnswers: false,
        filtersText: '',
      });
      return;
    }
    setNodeLabel(node.label);
    setNodeOrderIndex(String(node.orderIndex ?? 0));
    setNodeParentId(node.parentId == null ? ROOT_SELECT : String(node.parentId));
    setNodeBinding({
      datasetBinding: node.datasetBinding ?? 'ROSTER',
      bindingCourseId: node.bindingCourseId == null ? ROOT_SELECT : String(node.bindingCourseId),
      identifiable: Boolean(node.identifiable),
      includeAnswers: Boolean(node.includeAnswers),
      filtersText: node.filters == null ? '' : JSON.stringify(node.filters, null, 2),
    });
  }

  async function refreshWorkspace(nextId?: number) {
    const id = nextId ?? workspace?.id;
    if (!id) return;
    setIsLoadingWorkspace(true);
    try {
      const next = await getWorkspace(id);
      seedWorkspace(next);
    } catch (error) {
      toast.error(toErrorMessage(error));
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
        scopeCourseId:
          createScopeCourseId === ROOT_SELECT ? null : Number(createScopeCourseId),
      });
      seedWorkspace(created);
      setCreateName('');
      setCreateDescription('');
      setCreateScopeCourseId(ROOT_SELECT);
      toast.success('Workspace created.');
    } catch (error) {
      toast.error(toErrorMessage(error));
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
        description: workspaceDescription.trim(),
        status: workspaceStatus,
      });
      seedWorkspace(updated);
      toast.success('Workspace saved.');
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsSavingWorkspace(false);
    }
  }

  function toggleFolder(nodeId: number) {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }

  function startRename(node: PackageNode) {
    setEditingNodeId(node.id);
    setEditingLabel(node.label);
    setSelectedNodeId(node.id);
    hydrateNodeForm(node);
    setAddCursor(null);
  }

  async function handleRename(node: PackageNode) {
    const nextLabel = editingLabel.trim();
    if (!nextLabel || !workspace) {
      setEditingNodeId(null);
      return;
    }
    if (nextLabel === node.label) {
      setEditingNodeId(null);
      return;
    }
    setIsSavingNode(true);
    try {
      await updateNode(workspace.id, node.id, { label: nextLabel });
      setEditingNodeId(null);
      await refreshWorkspace();
      toast.success('Node renamed.');
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsSavingNode(false);
    }
  }

  function startAdd(parentId: 'ROOT' | number, kind: 'FOLDER' | 'FILE') {
    setAddCursor({ parentId, kind, label: '' });
    setSelectedNodeId(null);
    setEditingNodeId(null);
  }

  async function handleAddNode() {
    if (!workspace || !addCursor || !addCursor.label.trim()) return;
    setIsSavingNode(true);
    try {
      const parentId = addCursor.parentId === 'ROOT' ? null : addCursor.parentId;
      const siblings = workspace.nodes.filter((candidate) => candidate.parentId === parentId);
      const orderIndex = siblings.length;
      await addNode(workspace.id, {
        parentId,
        nodeType: addCursor.kind,
        label: addCursor.label.trim(),
        orderIndex,
        datasetBinding: addCursor.kind === 'FILE' ? 'ROSTER' : null,
        bindingCourseId: null,
        filters: null,
        identifiable: false,
        includeAnswers: false,
      });
      setAddCursor(null);
      await refreshWorkspace();
      if (parentId != null) {
        setExpandedFolders((prev) => new Set(prev).add(parentId));
      }
      toast.success(`${addCursor.kind.toLowerCase()} created.`);
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsSavingNode(false);
    }
  }

  function cancelAdd() {
    setAddCursor(null);
  }

  function updateSiblingOrder(nodes: PackageNode[], nodeA: PackageNode, nodeB: PackageNode) {
    if (!workspace) return;
    setIsSavingNode(true);
    Promise.resolve()
      .then(() =>
        Promise.all([
          updateNode(workspace.id, nodeA.id, { orderIndex: nodeB.orderIndex, parentId: nodeA.parentId }),
          updateNode(workspace.id, nodeB.id, { orderIndex: nodeA.orderIndex, parentId: nodeB.parentId }),
        ]),
      )
      .then(() => refreshWorkspace())
      .then(() => toast.success('Node order updated.'))
      .catch((error) => {
        toast.error(toErrorMessage(error));
      })
      .finally(() => {
        setIsSavingNode(false);
      });
  }

  async function handleMoveNode(node: PackageNode, direction: -1 | 1) {
    if (!workspace) return;
    const siblings = sortNodes(workspace.nodes.filter((candidate) => candidate.parentId === node.parentId));
    const index = siblings.findIndex((candidate) => candidate.id === node.id);
    const targetIndex = index + direction;
    if (index < 0 || targetIndex < 0 || targetIndex >= siblings.length) return;
    const target = siblings[targetIndex];
    await updateSiblingOrder(siblings, node, target);
  }

  async function handleDeleteNode(node: PackageNode) {
    if (!workspace) return;
    if (!window.confirm(`Delete ${node.label} and all children?`)) return;
    setIsSavingNode(true);
    try {
      await deleteNode(workspace.id, node.id);
      setSelectedNodeId((prev) => (prev === node.id ? null : prev));
      await refreshWorkspace();
      toast.success('Node deleted.');
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsSavingNode(false);
    }
  }

  function selectNode(node: PackageNode) {
    setSelectedNodeId(node.id);
    hydrateNodeForm(node);
    setEditingNodeId(null);
    setAddCursor(null);
    if (node.nodeType === 'FOLDER') {
      setExpandedFolders((prev) => new Set(prev).add(node.id));
    }
  }

  async function handleSaveNodeProperties() {
    if (!workspace || !selectedNode) return;
    setIsSavingNode(true);
    try {
      const orderIndex = Number(nodeOrderIndex);
      const payload = {
        label: nodeLabel.trim() || selectedNode.label,
        parentId: nodeParentId === ROOT_SELECT ? null : Number(nodeParentId),
        orderIndex: Number.isFinite(orderIndex) ? orderIndex : selectedNode.orderIndex,
      };
      const updates =
        selectedNode.nodeType === 'FILE'
          ? {
              ...payload,
              datasetBinding: nodeBinding.datasetBinding,
              bindingCourseId:
                nodeBinding.bindingCourseId === ROOT_SELECT
                  ? null
                  : Number(nodeBinding.bindingCourseId),
              filters: nodeBinding.filtersText.trim() ? parseFilters(nodeBinding.filtersText) : null,
              identifiable: nodeBinding.identifiable,
              includeAnswers: nodeBinding.includeAnswers,
            }
          : {
              ...payload,
              datasetBinding: null,
              bindingCourseId: null,
              filters: null,
              identifiable: false,
              includeAnswers: false,
            };
      await updateNode(workspace.id, selectedNode.id, updates);
      await refreshWorkspace();
      toast.success('Node updated.');
    } catch (error) {
      const errorMessage = toErrorMessage(error);
      toast.error(errorMessage);
    } finally {
      setIsSavingNode(false);
    }
  }

  function handleValidateWorkspace() {
    if (!workspace) return;
    setIsValidating(true);
    validateWorkspace(workspace.id, {
      strictMode,
      snapshotId: snapshotIdText ? Number(snapshotIdText) : undefined,
    })
      .then((result) => {
        setValidationResult(result);
        if (result.valid) {
          toast.success('Workspace is valid.');
        } else {
          toast.error('Validation failed.');
        }
      })
      .catch((error) => {
        const responseData = (error as { response?: { data?: ValidationResult } })?.response?.data;
        if (responseData && typeof responseData === 'object' && 'valid' in responseData) {
          setValidationResult(responseData);
        }
        toast.error(toErrorMessage(error));
      })
      .finally(() => {
        setIsValidating(false);
      });
  }

  async function handleBuildWorkspace() {
    if (!workspace) return;
    setIsBuilding(true);
    try {
      const job = await buildWorkspace(workspace.id, {
        strictMode,
        snapshotId: snapshotIdText ? Number(snapshotIdText) : undefined,
      });
      setBuildResult(job);
      if (job.status === 'COMPLETED') {
        toast.success('Package build completed.');
      } else if (job.errorMessage) {
        toast.error(job.errorMessage);
      } else {
        toast.error('Package build failed.');
      }
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsBuilding(false);
    }
  }

  async function handleDownloadArtifact() {
    if (!buildResult?.artifactId) return;
    setIsDownloadingArtifact(true);
    try {
      const { blob, filename } = await downloadArtifact(buildResult.artifactId);
      triggerBrowserDownload(blob, filename);
      toast.success('Download started.');
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsDownloadingArtifact(false);
    }
  }

  function renderNode(node: PackageNode, depth: number) {
    const isFolder = node.nodeType === 'FOLDER';
    const isExpanded = expandedFolders.has(node.id);
    const children = childrenMap.get(String(node.id)) ?? [];
    const siblings = sortNodes(workspace?.nodes.filter((candidate) => candidate.parentId === node.parentId) ?? []);
    const index = siblings.findIndex((candidate) => candidate.id === node.id);
    const canMoveUp = index > 0;
    const canMoveDown = index >= 0 && index + 1 < siblings.length;
    const isEditing = editingNodeId === node.id;
    const addingToThis =
      addCursor?.parentId === node.id;

    return (
      <div key={node.id} className="select-none">
        <div className={`group flex min-h-9 items-center gap-2 rounded-md px-2 py-1 text-sm ${selectedNodeId === node.id ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/30'}`}>
          <div className="flex items-center gap-2 min-w-0 flex-1">
            {isFolder && (
              <button
                type="button"
                className="rounded px-1 text-muted-foreground hover:bg-accent"
                onClick={(event) => {
                  event.stopPropagation();
                  toggleFolder(node.id);
                }}
                title={isExpanded ? 'Collapse folder' : 'Expand folder'}
              >
                {children.length ? (
                  isExpanded ? (
                    <ChevronDown className="size-4" />
                  ) : (
                    <ChevronRight className="size-4" />
                  )
                ) : (
                  <span className="inline-block w-4" />
                )}
              </button>
            )}
            {!isFolder && <span className="w-4" />}
            {isFolder ? (
              isExpanded ? <FolderOpen className="size-4 text-amber-500" /> : <Folder className="size-4 text-amber-500" />
            ) : (
              <File className="size-4 text-sky-500" />
            )}
            <button
              type="button"
              onClick={() => selectNode(node)}
              className="truncate font-medium text-foreground hover:underline text-left"
            >
              {isEditing ? (
                <Input
                  value={editingLabel}
                  onChange={(event) => setEditingLabel(event.target.value)}
                  onClick={(event) => {
                    event.stopPropagation();
                  }}
                  className="h-7 w-52"
                  autoFocus
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      void handleRename(node);
                    }
                    if (event.key === 'Escape') {
                      setEditingNodeId(null);
                    }
                  }}
                  onBlur={() => void handleRename(node)}
                />
              ) : (
                <span>{node.label}</span>
              )}
            </button>
          </div>
          <div className="ml-auto flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              type="button"
              className="rounded p-1 text-muted-foreground hover:bg-accent"
              onClick={(event) => {
                event.stopPropagation();
                startRename(node);
              }}
              title="Rename"
            >
              <Pencil className="size-4" />
            </button>
            <button
              type="button"
              className="rounded p-1 text-muted-foreground hover:bg-accent disabled:opacity-40"
              onClick={(event) => {
                event.stopPropagation();
                void handleMoveNode(node, -1);
              }}
              disabled={!canMoveUp || isSavingNode}
              title="Move up"
            >
              <MoveUp className="size-4" />
            </button>
            <button
              type="button"
              className="rounded p-1 text-muted-foreground hover:bg-accent disabled:opacity-40"
              onClick={(event) => {
                event.stopPropagation();
                void handleMoveNode(node, 1);
              }}
              disabled={!canMoveDown || isSavingNode}
              title="Move down"
            >
              <MoveDown className="size-4" />
            </button>
            {isFolder ? (
              <>
                <button
                  type="button"
                  className="rounded p-1 text-muted-foreground hover:bg-accent"
                  onClick={(event) => {
                    event.stopPropagation();
                    startAdd(node.id, 'FOLDER');
                  }}
                  title="Add folder"
                >
                  <FolderPlus className="size-4" />
                </button>
                <button
                  type="button"
                  className="rounded p-1 text-muted-foreground hover:bg-accent"
                  onClick={(event) => {
                    event.stopPropagation();
                    startAdd(node.id, 'FILE');
                  }}
                  title="Add file"
                >
                  <FilePlus className="size-4" />
                </button>
              </>
            ) : null}
            <button
              type="button"
              className="rounded p-1 text-destructive hover:bg-accent"
              onClick={(event) => {
                event.stopPropagation();
                void handleDeleteNode(node);
              }}
              title="Delete"
            >
              <Trash2 className="size-4" />
            </button>
          </div>
        </div>

        {isFolder && isExpanded ? (
          <div className="space-y-1 pl-5">
            {children.length === 0 ? (
              <p className="px-2 py-1 text-xs text-muted-foreground">No children</p>
            ) : (
              children.map((child) => renderNode(child, depth + 1))
            )}
          </div>
        ) : null}

        {addingToThis ? (
          <div className="pl-10">
            <div className="mt-1 flex items-center gap-2">
              <Input
                value={addCursor?.label ?? ''}
                onChange={(event) =>
                  setAddCursor(
                    (prev) =>
                      prev && {
                        ...prev,
                        label: event.target.value,
                      },
                  )
                }
                onKeyDown={(event) => {
                  if (event.key === 'Enter') void handleAddNode();
                  if (event.key === 'Escape') cancelAdd();
                }}
                placeholder={`New ${addCursor?.kind.toLowerCase()}`}
                className="h-7"
              />
              <Button type="button" size="sm" onClick={() => void handleAddNode()}>
                Add
              </Button>
              <Button type="button" size="sm" variant="outline" onClick={cancelAdd}>
                Cancel
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  const rootNodes = childrenMap.get('ROOT') ?? [];

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Package Workspaces</h1>
        <p className="text-muted-foreground mt-1">
          Build export packages with a real file-explorer style tree and file-level controls.
        </p>
      </div>

      <section className="rounded-sm border border-border bg-card p-4 space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Workspace</h2>
        <div className="grid gap-3 md:grid-cols-[1.1fr_1fr_1fr_1fr_auto]">
          <div className="space-y-1">
            <Label>Workspace ID</Label>
            <div className="flex gap-2">
              <Input value={workspaceIdInput} onChange={(event) => setWorkspaceIdInput(event.target.value)} />
              <Button type="button" onClick={() => void handleOpenWorkspace()} disabled={isLoadingWorkspace}>
                <RefreshCw className="mr-2 size-4" />
                Open
              </Button>
            </div>
          </div>
          <div className="space-y-1">
            <Label>Name</Label>
            <Input value={createName} onChange={(event) => setCreateName(event.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>Scope Course</Label>
            <Select value={createScopeCourseId} onValueChange={setCreateScopeCourseId}>
              <SelectTrigger>
                <SelectValue placeholder="Unscoped" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ROOT_SELECT}>Unscoped</SelectItem>
                {courses.map((course) => (
                  <SelectItem key={course.id} value={String(course.id)}>
                    {course.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Description</Label>
            <Input
              value={createDescription}
              onChange={(event) => setCreateDescription(event.target.value)}
              placeholder="Optional"
            />
          </div>
          <div className="space-y-1 flex items-end">
            <Button type="button" onClick={() => void handleCreateWorkspace()} disabled={isLoadingWorkspace}>
              <Plus className="mr-2 size-4" />
              Create
            </Button>
          </div>
        </div>
      </section>

      {!workspace ? (
        <div className="rounded-sm border border-border bg-card p-8 text-sm text-muted-foreground text-center">
          Open an existing workspace or create a new one to start.
        </div>
      ) : (
        <>
          <section className="rounded-sm border border-border bg-card p-4">
            <div className="mb-3 flex justify-between items-center">
              <div>
                <h2 className="text-lg font-semibold text-foreground">
                  Workspace #{workspace.id} · Revision {workspace.revision}
                </h2>
                <p className="text-xs text-muted-foreground">
                  Updated {new Date(workspace.updatedAt).toLocaleString()}
                </p>
              </div>
              <Button type="button" onClick={() => void handleSaveWorkspace()} disabled={isSavingWorkspace}>
                <Save className="mr-2 size-4" />
                {isSavingWorkspace ? 'Saving...' : 'Save metadata'}
              </Button>
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              <div className="space-y-1">
                <Label>Name</Label>
                <Input value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} />
              </div>
              <div className="space-y-1">
                <Label>Status</Label>
                <Select value={workspaceStatus} onValueChange={(value) => setWorkspaceStatus(value as WorkspaceStatus)}>
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
                <Input value={workspace.scopeCourseId ?? 'Unscoped'} readOnly />
              </div>
              <div className="space-y-1">
                <Label>Description</Label>
                <Input value={workspaceDescription} onChange={(event) => setWorkspaceDescription(event.target.value)} />
              </div>
            </div>
          </section>

          <div className="grid gap-4 xl:grid-cols-[1fr_1.15fr]">
            <section className="rounded-sm border border-border bg-card p-4">
              <div className="mb-3 flex justify-between items-center">
                <h2 className="text-lg font-semibold text-foreground">Explorer</h2>
                <div className="flex gap-2">
                  <Button type="button" size="sm" variant="outline" onClick={() => startAdd('ROOT', 'FOLDER')}>
                    <FolderPlus className="mr-2 size-4" />
                    Folder
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={() => startAdd('ROOT', 'FILE')}>
                    <FilePlus className="mr-2 size-4" />
                    File
                  </Button>
                </div>
              </div>

              {addCursor && addCursor.parentId === 'ROOT' ? (
                <div className="mb-3 flex gap-2">
                  <Input
                    value={addCursor.label}
                    onChange={(event) =>
                      setAddCursor((prev) =>
                        prev ? { ...prev, label: event.target.value } : prev,
                      )
                    }
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') void handleAddNode();
                      if (event.key === 'Escape') cancelAdd();
                    }}
                    placeholder={`New ${addCursor.kind.toLowerCase()} at root`}
                  />
                  <Button type="button" onClick={() => void handleAddNode()}>
                    Add
                  </Button>
                  <Button type="button" variant="outline" onClick={cancelAdd}>
                    Cancel
                  </Button>
                </div>
              ) : null}

              <div className="space-y-1">
                {rootNodes.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No nodes yet.</p>
                ) : (
                  rootNodes.map((node) => renderNode(node, 0))
                )}
              </div>
            </section>

            <section className="space-y-4">
              <div className="rounded-sm border border-border bg-card p-4 space-y-3">
                <h2 className="text-lg font-semibold text-foreground">Selected Node</h2>
                {!selectedNode ? (
                  <p className="text-sm text-muted-foreground">
                    Select any node in the tree to edit file bindings, parent, and order.
                  </p>
                ) : (
                  <div className="space-y-3">
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="space-y-1 md:col-span-2">
                        <Label>Label</Label>
                        <Input value={nodeLabel} onChange={(event) => setNodeLabel(event.target.value)} />
                      </div>
                      <div className="space-y-1">
                        <Label>Order</Label>
                        <Input value={nodeOrderIndex} onChange={(event) => setNodeOrderIndex(event.target.value)} />
                      </div>
                      <div className="space-y-1">
                        <Label>Parent</Label>
                        <Select value={nodeParentId} onValueChange={setNodeParentId}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value={ROOT_SELECT}>Root</SelectItem>
                            {workspace.nodes
                              .filter((candidate) => candidate.id !== selectedNode.id && candidate.nodeType === 'FOLDER')
                              .map((candidate) => (
                                <SelectItem key={candidate.id} value={String(candidate.id)}>
                                  {candidate.label}
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {selectedNode.nodeType === 'FILE' ? (
                      <div className="space-y-3 border border-border p-3 rounded-sm">
                        <div className="grid gap-3 md:grid-cols-2">
                          <div className="space-y-1">
                            <Label>Dataset Binding</Label>
                            <Select
                              value={nodeBinding.datasetBinding}
                              onValueChange={(value) =>
                                setNodeBinding((prev) => ({
                                  ...prev,
                                  datasetBinding: value as DatasetBinding,
                                }))
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
                            <Label>Binding Course</Label>
                            <Select
                              value={nodeBinding.bindingCourseId}
                              onValueChange={(value) =>
                                setNodeBinding((prev) => ({ ...prev, bindingCourseId: value }))
                              }
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="Select course" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value={ROOT_SELECT}>None</SelectItem>
                                {courses.map((course) => (
                                  <SelectItem key={course.id} value={String(course.id)}>
                                    {course.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-1 md:col-span-2">
                            <Label>Filters (JSON)</Label>
                            <Input
                              value={nodeBinding.filtersText}
                              onChange={(event) =>
                                setNodeBinding((prev) => ({ ...prev, filtersText: event.target.value }))
                              }
                              placeholder="{}"
                            />
                          </div>
                          <label className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Checkbox
                              checked={nodeBinding.identifiable}
                              disabled={!canExportIdentifiable}
                              onCheckedChange={(checked) =>
                                setNodeBinding((prev) => ({ ...prev, identifiable: checked === true }))
                              }
                            />
                            Identifiable output
                          </label>
                          <label className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Checkbox
                              checked={nodeBinding.includeAnswers}
                              onCheckedChange={(checked) =>
                                setNodeBinding((prev) => ({ ...prev, includeAnswers: checked === true }))
                              }
                            />
                            Include answers
                          </label>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">File settings are available only for files.</p>
                    )}

                    <div className="flex gap-2">
                      <Button type="button" onClick={() => void handleSaveNodeProperties()} disabled={isSavingNode}>
                        <Save className="mr-2 size-4" />
                        {isSavingNode ? 'Saving...' : 'Save'}
                      </Button>
                      <Button type="button" variant="destructive" onClick={() => void handleDeleteNode(selectedNode)}>
                        <Trash2 className="mr-2 size-4" />
                        Delete node
                      </Button>
                    </div>
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
                    <Label>Snapshot ID</Label>
                    <Input
                      value={snapshotIdText}
                      onChange={(event) => setSnapshotIdText(event.target.value)}
                      placeholder="Leave empty for live"
                    />
                  </div>
                  <div className="flex gap-2 items-end">
                    <Button type="button" onClick={() => handleValidateWorkspace()} disabled={isValidating}>
                      {isValidating ? 'Validating...' : 'Validate'}
                    </Button>
                    <Button type="button" variant="outline" onClick={() => void handleBuildWorkspace()} disabled={isBuilding}>
                      {isBuilding ? 'Building...' : 'Build'}
                    </Button>
                  </div>
                </div>
                {validationResult && (
                  <div className="rounded-sm border border-border p-3 text-sm space-y-2">
                    <p className="font-medium text-foreground">
                      Validation: {validationResult.valid ? 'valid' : 'invalid'} · Files {validationResult.fileCount} ·
                      Estimated rows {validationResult.estimatedRows}
                    </p>
                    {validationResult.violations.length > 0 && (
                      <div>
                        <p className="font-medium text-destructive">Violations</p>
                        <ul className="list-disc pl-5 text-muted-foreground">
                          {validationResult.violations.map((issue, index) => (
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
                  <div className="rounded-sm border border-border p-3 text-sm space-y-2">
                    <p className="font-medium text-foreground">
                      Build #{buildResult.id}: {buildResult.status}
                    </p>
                    {buildResult.artifactId && <p className="text-muted-foreground">Artifact: {buildResult.artifactId}</p>}
                    {buildResult.errorMessage && <p className="text-destructive">{buildResult.errorMessage}</p>}
                    {buildResult.artifactId && buildResult.status === 'COMPLETED' && (
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => void handleDownloadArtifact()}
                        disabled={isDownloadingArtifact}
                      >
                        <Download className="mr-2 size-4" />
                        {isDownloadingArtifact ? 'Downloading...' : 'Download artifact'}
                      </Button>
                    )}
                  </div>
                )}
                {!canExportIdentifiable && role === 'RESEARCHER' ? (
                  <p className="text-xs text-muted-foreground">
                    Identifiable output is disabled. Grant EXPORT_IDENTIFIABLE in sudo capabilities to enable.
                  </p>
                ) : null}
              </section>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
