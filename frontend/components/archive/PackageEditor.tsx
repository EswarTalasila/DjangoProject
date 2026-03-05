'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  ChevronsDownUp,
  ChevronsUpDown,
  File,
  FilePlus,
  FileText,
  Folder,
  FolderOpen,
  FolderPlus,
  GripVertical,
  MoveDown,
  MoveUp,
  Pencil,
  Save,
  Trash2,
  Users,
} from 'lucide-react';
import { toast } from 'sonner';

import DataCatalog from '@/components/archive/DataCatalog';
import PackageBuildBar from '@/components/archive/PackageBuildBar';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { HelpTip } from '@/components/ui/help-tip';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { StatusBadge } from '@/components/ui/status-badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { listCourses, type CourseSummary } from '@/lib/course-api';
import {
  addNode,
  buildWorkspace,
  deleteNode,
  downloadArtifact,
  getWorkspace,
  reorderNode,
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
import { toErrorMessage, triggerBrowserDownload } from '@/lib/utils';

type PackageEditorProps = {
  workspaceId: number;
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
  canExportIdentifiable: boolean;
  onBack: () => void;
};

type AddCursor = {
  parentId: 'ROOT' | number;
  kind: 'FOLDER' | 'FILE';
  label: string;
};

type NodeBindingForm = {
  datasetBinding: DatasetBinding;
  bindingCourseId: string;
  identifiable: boolean;
  includeAnswers: boolean;
  filtersText: string;
};

const DATA_SOURCES: Array<{ value: DatasetBinding; label: string }> = [
  { value: 'ROSTER', label: 'Roster CSV' },
  { value: 'COURSE_SUBMISSIONS', label: 'Course Submissions CSV' },
  { value: 'CROSS_COURSE_SUBMISSIONS', label: 'Cross-Course Submissions CSV' },
];

const NONE_SELECT = '__ROOT__';

/* ---------------------------------------------------------------------------
 * Utility helpers (preserved from original)
 * --------------------------------------------------------------------------- */

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

function getBuildErrorMessage(raw: string | undefined): string {
  if (!raw) return 'Package creation failed.';
  try {
    const parsed = JSON.parse(raw) as Array<{ message?: string }> | unknown;
    if (Array.isArray(parsed) && parsed.length > 0) {
      const first = parsed[0];
      if (
        first &&
        typeof first === 'object' &&
        'message' in first &&
        typeof first.message === 'string'
      ) {
        return first.message;
      }
    }
  } catch {
    // fall through and return raw string
  }
  return raw;
}

/* ---------------------------------------------------------------------------
 * File icon helper — colors icon based on datasetBinding
 * --------------------------------------------------------------------------- */

function FileIcon({
  node,
}: {
  node: PackageNode;
}) {
  if (node.nodeType === 'FOLDER') {
    return null; // handled separately in renderNode
  }
  switch (node.datasetBinding) {
    case 'ROSTER':
      return <Users className="size-4 text-green-500" />;
    case 'COURSE_SUBMISSIONS':
    case 'CROSS_COURSE_SUBMISSIONS':
      return <FileText className="size-4 text-purple-500" />;
    default:
      return <File className="size-4 text-sky-500" />;
  }
}

/* ---------------------------------------------------------------------------
 * Component
 * --------------------------------------------------------------------------- */

export default function PackageEditor({
  workspaceId,
  role,
  canExportIdentifiable,
  onBack,
}: PackageEditorProps) {
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [coursesLoaded, setCoursesLoaded] = useState(false);

  const [workspace, setWorkspace] = useState<PackageWorkspace | null>(null);

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
  const [nodeParentId, setNodeParentId] = useState(NONE_SELECT);
  const [nodeBinding, setNodeBinding] = useState<NodeBindingForm>({
    datasetBinding: 'ROSTER',
    bindingCourseId: NONE_SELECT,
    identifiable: false,
    includeAnswers: false,
    filtersText: '',
  });

  const [strictMode, setStrictMode] = useState(true);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [buildResult, setBuildResult] = useState<BuildJob | null>(null);

  const [isLoadingWorkspace, setIsLoadingWorkspace] = useState(false);
  const [isSavingWorkspace, setIsSavingWorkspace] = useState(false);
  const [isSavingNode, setIsSavingNode] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isBuilding, setIsBuilding] = useState(false);
  const [isDownloadingArtifact, setIsDownloadingArtifact] = useState(false);

  /* Drag-and-drop state */
  const [draggedNodeId, setDraggedNodeId] = useState<number | null>(null);
  const [dropTargetId, setDropTargetId] = useState<number | 'ROOT' | null>(null);

  const childrenMap = useMemo(
    () => buildChildrenMap(workspace?.nodes ?? []),
    [workspace?.nodes],
  );

  const selectedNode = useMemo(
    () => workspace?.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [workspace?.nodes, selectedNodeId],
  );

  /* --- Load on mount --- */

  useEffect(() => {
    void loadCourses();
    void refreshWorkspace(workspaceId);
  }, [workspaceId]);

  /* --- Data loading --- */

  async function loadCourses() {
    if (coursesLoaded) return;
    try {
      const list = await listCourses();
      setCourses(list);
      setCoursesLoaded(true);
    } catch (error) {
      toast.error(toErrorMessage(error));
    }
  }

  function seedWorkspace(next: PackageWorkspace) {
    setWorkspace(next);
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
      setNodeParentId(NONE_SELECT);
      setNodeBinding({
        datasetBinding: 'ROSTER',
        bindingCourseId: NONE_SELECT,
        identifiable: false,
        includeAnswers: false,
        filtersText: '',
      });
      return;
    }
    setNodeLabel(node.label);
    setNodeOrderIndex(String(node.orderIndex ?? 0));
    setNodeParentId(node.parentId == null ? NONE_SELECT : String(node.parentId));
    setNodeBinding({
      datasetBinding: node.datasetBinding ?? 'ROSTER',
      bindingCourseId:
        node.bindingCourseId == null ? NONE_SELECT : String(node.bindingCourseId),
      identifiable: Boolean(node.identifiable),
      includeAnswers: Boolean(node.includeAnswers),
      filtersText:
        node.filters == null ? '' : JSON.stringify(node.filters, null, 2),
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

  /* --- Workspace metadata --- */

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
      toast.success('Package saved.');
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsSavingWorkspace(false);
    }
  }

  /* --- Tree interaction --- */

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

  function expandAll() {
    if (!workspace) return;
    const folderIds = workspace.nodes
      .filter((node) => node.nodeType === 'FOLDER')
      .map((node) => node.id);
    setExpandedFolders(new Set(folderIds));
  }

  function collapseAll() {
    setExpandedFolders(new Set());
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
      toast.success('Renamed.');
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
      const siblings = workspace.nodes.filter(
        (candidate) => candidate.parentId === parentId,
      );
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
      const kindLabel = addCursor.kind === 'FOLDER' ? 'Folder' : 'File';
      setAddCursor(null);
      await refreshWorkspace();
      if (parentId != null) {
        setExpandedFolders((prev) => new Set(prev).add(parentId));
      }
      toast.success(`${kindLabel} created.`);
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsSavingNode(false);
    }
  }

  function cancelAdd() {
    setAddCursor(null);
  }

  async function updateSiblingOrder(
    nodeA: PackageNode,
    nodeB: PackageNode,
  ) {
    if (!workspace) return;
    setIsSavingNode(true);
    try {
      await Promise.all([
        updateNode(workspace.id, nodeA.id, {
          orderIndex: nodeB.orderIndex,
          parentId: nodeA.parentId,
        }),
        updateNode(workspace.id, nodeB.id, {
          orderIndex: nodeA.orderIndex,
          parentId: nodeB.parentId,
        }),
      ]);
      await refreshWorkspace();
      toast.success('Order updated.');
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsSavingNode(false);
    }
  }

  async function handleMoveNode(node: PackageNode, direction: -1 | 1) {
    if (!workspace) return;
    const siblings = sortNodes(
      workspace.nodes.filter(
        (candidate) => candidate.parentId === node.parentId,
      ),
    );
    const index = siblings.findIndex((candidate) => candidate.id === node.id);
    const targetIndex = index + direction;
    if (index < 0 || targetIndex < 0 || targetIndex >= siblings.length) return;
    const target = siblings[targetIndex];
    await updateSiblingOrder(node, target);
  }

  async function handleDropNode(movedId: number, targetParentId: number | null) {
    if (!workspace) return;
    const movedNode = workspace.nodes.find((n) => n.id === movedId);
    if (!movedNode) return;
    if (movedNode.parentId === targetParentId) return;
    if (targetParentId === movedId) return;
    /* Cyclic-move guard: don't drop a folder into its own descendant */
    if (targetParentId != null && movedNode.nodeType === 'FOLDER') {
      let current = workspace.nodes.find((n) => n.id === targetParentId);
      while (current) {
        if (current.id === movedId) {
          toast.error('Cannot move a folder into its own descendant.');
          return;
        }
        current = current.parentId != null
          ? workspace.nodes.find((n) => n.id === current!.parentId)
          : undefined;
      }
    }
    setIsSavingNode(true);
    try {
      const targetChildren = workspace.nodes.filter(
        (n) => n.parentId === targetParentId && n.id !== movedId,
      );
      const updated = await reorderNode(workspace.id, {
        movedNodeId: movedId,
        targetParentId,
        targetOrderIndex: targetChildren.length,
      });
      seedWorkspace(updated);
      if (targetParentId != null) {
        setExpandedFolders((prev) => new Set(prev).add(targetParentId));
      }
      toast.success('Moved.');
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsSavingNode(false);
    }
  }

  async function handleDeleteNode(node: PackageNode) {
    if (!workspace) return;
    if (!window.confirm(`Delete "${node.label}" and all contents?`)) return;
    setIsSavingNode(true);
    try {
      await deleteNode(workspace.id, node.id);
      setSelectedNodeId((prev) => (prev === node.id ? null : prev));
      await refreshWorkspace();
      toast.success('Deleted.');
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

  /* --- Node properties --- */

  async function handleSaveNodeProperties() {
    if (!workspace || !selectedNode) return;
    setIsSavingNode(true);
    try {
      const orderIndex = Number(nodeOrderIndex);
      const payload = {
        label: nodeLabel.trim() || selectedNode.label,
        parentId: nodeParentId === NONE_SELECT ? null : Number(nodeParentId),
        orderIndex: Number.isFinite(orderIndex)
          ? orderIndex
          : selectedNode.orderIndex,
      };
      const updates =
        selectedNode.nodeType === 'FILE'
          ? {
              ...payload,
              datasetBinding: nodeBinding.datasetBinding,
              bindingCourseId:
                nodeBinding.bindingCourseId === NONE_SELECT
                  ? null
                  : Number(nodeBinding.bindingCourseId),
              filters: nodeBinding.filtersText.trim()
                ? parseFilters(nodeBinding.filtersText)
                : null,
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
      toast.success('Item saved.');
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsSavingNode(false);
    }
  }

  /* --- Validate & Build --- */

  function handleValidateWorkspace() {
    if (!workspace) return;
    setIsValidating(true);
    validateWorkspace(workspace.id, {
      strictMode,
    })
      .then((result) => {
        setValidationResult(result);
        if (result.valid) {
          toast.success('No issues found.');
        } else {
          toast.error('Some issues were found.');
        }
      })
      .catch((error) => {
        const responseData = (
          error as { response?: { data?: ValidationResult } }
        )?.response?.data;
        if (
          responseData &&
          typeof responseData === 'object' &&
          'valid' in responseData
        ) {
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
      toast.info(
        'Live data sources will be snapshotted automatically at build start.',
      );
      const job = await buildWorkspace(workspace.id, {
        strictMode,
      });
      setBuildResult(job);
      if (job.status === 'COMPLETED') {
        toast.success('Package created successfully.');
      } else if (job.errorMessage) {
        toast.error(getBuildErrorMessage(job.errorMessage));
      } else {
        toast.error('Package creation failed.');
      }
    } catch (error) {
      const status = (error as { response?: { status?: number } })?.response
        ?.status;
      if (status === 401) {
        toast.error('Session expired. Please sign in again.');
      } else {
        toast.error(toErrorMessage(error));
      }
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

  /* --- Catalog add handler --- */

  async function handleAddFromCatalog(config: {
    label: string;
    datasetBinding: DatasetBinding;
    bindingCourseId: number | null;
    sourceType?: 'LIVE' | 'SNAPSHOT';
    snapshotId?: number | null;
  }) {
    if (!workspace) return;
    setIsSavingNode(true);
    try {
      /* Determine parent: use currently-selected folder, or root */
      const parentFolder =
        selectedNode?.nodeType === 'FOLDER' ? selectedNode.id : null;
      const siblings = workspace.nodes.filter(
        (candidate) => candidate.parentId === parentFolder,
      );
      const orderIndex = siblings.length;
      await addNode(workspace.id, {
        parentId: parentFolder,
        nodeType: 'FILE',
        label: config.label,
        orderIndex,
        datasetBinding: config.datasetBinding,
        bindingCourseId: config.bindingCourseId,
        filters: null,
        identifiable: false,
        includeAnswers: false,
        sourceType: config.sourceType ?? 'LIVE',
        snapshotId: config.snapshotId ?? null,
      });
      await refreshWorkspace();
      /* Auto-expand the parent folder so the new file is visible */
      if (parentFolder != null) {
        setExpandedFolders((prev) => new Set(prev).add(parentFolder));
      }
      toast.success('File added from catalog.');
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsSavingNode(false);
    }
  }

  /* --- Tree renderer --- */

  function renderNode(node: PackageNode, depth: number) {
    const isFolder = node.nodeType === 'FOLDER';
    const isExpanded = expandedFolders.has(node.id);
    const children = childrenMap.get(String(node.id)) ?? [];
    const siblings = sortNodes(
      workspace?.nodes.filter(
        (candidate) => candidate.parentId === node.parentId,
      ) ?? [],
    );
    const index = siblings.findIndex((candidate) => candidate.id === node.id);
    const canMoveUp = index > 0;
    const canMoveDown = index >= 0 && index + 1 < siblings.length;
    const isEditing = editingNodeId === node.id;
    const addingToThis = addCursor?.parentId === node.id;

    return (
      <div
        key={node.id}
        className="select-none"
        draggable
        onDragStart={(e) => {
          e.dataTransfer.setData('application/node-id', String(node.id));
          e.dataTransfer.effectAllowed = 'move';
          setDraggedNodeId(node.id);
        }}
        onDragEnd={() => {
          setDraggedNodeId(null);
          setDropTargetId(null);
        }}
      >
        <div
          className={`group flex min-h-9 items-center gap-2 rounded-md px-2 py-1 text-sm ${
            selectedNodeId === node.id
              ? 'bg-accent text-foreground'
              : 'text-muted-foreground hover:bg-accent/30'
          }${draggedNodeId === node.id ? ' opacity-40' : ''}${dropTargetId === node.id && isFolder ? ' ring-2 ring-primary bg-primary/5' : ''}`}
          onDragOver={(e) => {
            if (isFolder && draggedNodeId != null && draggedNodeId !== node.id) {
              e.preventDefault();
              e.stopPropagation();
              setDropTargetId(node.id);
            }
          }}
          onDragLeave={() => {
            if (dropTargetId === node.id) setDropTargetId(null);
          }}
          onDrop={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setDropTargetId(null);
            if (draggedNodeId != null && isFolder) {
              void handleDropNode(draggedNodeId, node.id);
            }
          }}
        >
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <GripVertical className="size-3.5 shrink-0 cursor-grab text-muted-foreground/40 hover:text-muted-foreground" />
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
              isExpanded ? (
                <FolderOpen className="size-4 text-amber-500" />
              ) : (
                <Folder className="size-4 text-amber-500" />
              )
            ) : (
              <FileIcon node={node} />
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
            {node.nodeType === 'FILE' && node.sourceType === 'SNAPSHOT' && (
              <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-medium">
                Snapshot
              </span>
            )}
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
          <div className="ml-3 border-l border-border pl-3 space-y-1">
            {children.length === 0 ? (
              <p className="px-2 py-1 text-xs text-muted-foreground">
                Empty folder
              </p>
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
              <Button
                type="button"
                size="sm"
                onClick={() => void handleAddNode()}
              >
                Add
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={cancelAdd}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  /* --- Render --- */

  const rootNodes = childrenMap.get('ROOT') ?? [];

  if (isLoadingWorkspace && !workspace) {
    return (
      <div className="space-y-4 p-6">
        <Button type="button" variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="mr-2 size-4" />
          Back to packages
        </Button>
        <div className="rounded-sm border border-border bg-card p-8 text-sm text-muted-foreground text-center">
          Loading package...
        </div>
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="space-y-4 p-6">
        <Button type="button" variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="mr-2 size-4" />
          Back to packages
        </Button>
        <div className="rounded-sm border border-border bg-card p-8 text-sm text-muted-foreground text-center">
          Package not found. It may have been deleted or you do not have access.
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* ---- Compact header ---- */}
      <div className="flex items-center gap-3 border-b border-border bg-card px-4 py-3">
        <Button type="button" variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <Input
            value={workspaceName}
            onChange={(event) => setWorkspaceName(event.target.value)}
            className="h-8 max-w-xs font-semibold"
          />
          <StatusBadge status={workspaceStatus} />
          <span className="text-xs text-muted-foreground whitespace-nowrap hidden sm:inline">
            Updated {new Date(workspace.updatedAt).toLocaleString()}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={workspaceStatus}
            onValueChange={(value) =>
              setWorkspaceStatus(value as WorkspaceStatus)
            }
          >
            <SelectTrigger className="h-8 w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="DRAFT">Draft</SelectItem>
              <SelectItem value="SEALED">Ready</SelectItem>
            </SelectContent>
          </Select>
          <Button
            type="button"
            size="sm"
            onClick={() => void handleSaveWorkspace()}
            disabled={isSavingWorkspace}
          >
            <Save className="mr-2 size-4" />
            {isSavingWorkspace ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>

      {/* ---- Two-pane main area ---- */}
      <div className="flex-1 overflow-hidden grid grid-cols-1 xl:grid-cols-[1fr_1.2fr] gap-4 p-4">
        {/* Left pane: Explorer tree */}
        <section className="flex flex-col rounded-sm border border-border bg-card overflow-hidden">
          {/* Toolbar */}
          <div className="flex items-center gap-1 border-b border-border px-3 py-2">
            <span className="text-sm font-semibold text-foreground mr-auto">
              Explorer
            </span>
            <button
              type="button"
              className="rounded p-1.5 text-muted-foreground hover:bg-accent"
              onClick={() => startAdd('ROOT', 'FOLDER')}
              title="New folder at root"
            >
              <FolderPlus className="size-4" />
            </button>
            <button
              type="button"
              className="rounded p-1.5 text-muted-foreground hover:bg-accent"
              onClick={() => startAdd('ROOT', 'FILE')}
              title="New file at root"
            >
              <FilePlus className="size-4" />
            </button>
            <button
              type="button"
              className="rounded p-1.5 text-muted-foreground hover:bg-accent"
              onClick={expandAll}
              title="Expand all"
            >
              <ChevronsUpDown className="size-4" />
            </button>
            <button
              type="button"
              className="rounded p-1.5 text-muted-foreground hover:bg-accent"
              onClick={collapseAll}
              title="Collapse all"
            >
              <ChevronsDownUp className="size-4" />
            </button>
          </div>

          {/* Tree content */}
          <div className="flex-1 overflow-y-auto p-3 space-y-1">
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
                  className="h-7"
                />
                <Button
                  type="button"
                  size="sm"
                  onClick={() => void handleAddNode()}
                >
                  Add
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={cancelAdd}
                >
                  Cancel
                </Button>
              </div>
            ) : null}

            {rootNodes.length === 0 && !addCursor ? (
              <p className="text-sm text-muted-foreground py-6 text-center">
                Your package is empty. Add folders and files, then bind data
                from the catalog.
              </p>
            ) : (
              rootNodes.map((node) => renderNode(node, 0))
            )}

            {/* Root drop zone — appears during drag */}
            {draggedNodeId != null && (
              <div
                className={`mt-2 rounded-md border-2 border-dashed py-3 text-center text-xs ${
                  dropTargetId === 'ROOT'
                    ? 'border-primary bg-primary/5 text-foreground'
                    : 'border-border text-muted-foreground'
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setDropTargetId('ROOT');
                }}
                onDragLeave={() => {
                  if (dropTargetId === 'ROOT') setDropTargetId(null);
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setDropTargetId(null);
                  if (draggedNodeId != null) {
                    void handleDropNode(draggedNodeId, null);
                  }
                }}
              >
                Drop here to move to root
              </div>
            )}
          </div>
        </section>

        {/* Right pane: Catalog + Properties tabs */}
        <section className="flex flex-col rounded-sm border border-border bg-card overflow-hidden">
          <Tabs defaultValue="catalog" className="flex flex-col flex-1 overflow-hidden">
            <TabsList className="mx-3 mt-2 w-fit">
              <TabsTrigger value="catalog">Catalog</TabsTrigger>
              <TabsTrigger value="properties">Properties</TabsTrigger>
            </TabsList>

            {/* Catalog tab */}
            <TabsContent
              value="catalog"
              className="flex-1 overflow-y-auto px-3 pb-3"
            >
              <DataCatalog
                role={role}
                onAddItem={handleAddFromCatalog}
              />
            </TabsContent>

            {/* Properties tab */}
            <TabsContent
              value="properties"
              className="flex-1 overflow-y-auto px-3 pb-3"
            >
              {!selectedNode ? (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  Select an item in the tree to view its properties.
                </p>
              ) : (
                <div className="space-y-3 pt-1">
                  {/* Common fields: label, parent, order */}
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="space-y-1 md:col-span-2">
                      <Label className="flex items-center gap-1">
                        Label
                        <HelpTip text="A descriptive name for this item in the package tree." />
                      </Label>
                      <Input
                        value={nodeLabel}
                        onChange={(event) => setNodeLabel(event.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="flex items-center gap-1">
                        Order
                        <HelpTip text="Position within sibling items. Lower numbers appear first." />
                      </Label>
                      <Input
                        value={nodeOrderIndex}
                        onChange={(event) =>
                          setNodeOrderIndex(event.target.value)
                        }
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="flex items-center gap-1">
                        Parent
                        <HelpTip text="The folder this item belongs to." />
                      </Label>
                      <Select value={nodeParentId} onValueChange={setNodeParentId}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value={NONE_SELECT}>Root</SelectItem>
                          {workspace.nodes
                            .filter(
                              (candidate) =>
                                candidate.id !== selectedNode.id &&
                                candidate.nodeType === 'FOLDER',
                            )
                            .map((candidate) => (
                              <SelectItem
                                key={candidate.id}
                                value={String(candidate.id)}
                              >
                                {candidate.label}
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* File-specific fields */}
                  {selectedNode.nodeType === 'FILE' ? (
                    <div className="space-y-3 border border-border p-3 rounded-sm">
                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="space-y-1">
                          <Label className="flex items-center gap-1">
                            Data source
                            <HelpTip text="The type of data this file will contain when the package is built." />
                          </Label>
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
                              {DATA_SOURCES.map((binding) => (
                                <SelectItem
                                  key={binding.value}
                                  value={binding.value}
                                >
                                  {binding.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-1">
                          <Label className="flex items-center gap-1">
                            From Course
                            <HelpTip text="Select which course's data this file should contain." />
                          </Label>
                          <Select
                            value={nodeBinding.bindingCourseId}
                            onValueChange={(value) =>
                              setNodeBinding((prev) => ({
                                ...prev,
                                bindingCourseId: value,
                              }))
                            }
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select course" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value={NONE_SELECT}>None</SelectItem>
                              {courses.map((course) => (
                                <SelectItem
                                  key={course.id}
                                  value={String(course.id)}
                                >
                                  {course.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-1 md:col-span-2">
                          <Label className="flex items-center gap-1">
                            Filters (JSON)
                            <HelpTip text='Optional JSON object to narrow exported rows. Example: {"assignmentId": 5}' />
                          </Label>
                          <Input
                            value={nodeBinding.filtersText}
                            onChange={(event) =>
                              setNodeBinding((prev) => ({
                                ...prev,
                                filtersText: event.target.value,
                              }))
                            }
                            placeholder='e.g. {"assignmentId": 5}'
                          />
                        </div>
                        <label className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Checkbox
                            checked={nodeBinding.identifiable}
                            disabled={!canExportIdentifiable}
                            onCheckedChange={(checked) =>
                              setNodeBinding((prev) => ({
                                ...prev,
                                identifiable: checked === true,
                              }))
                            }
                          />
                          Identifiable
                          <HelpTip text="Include student names and email addresses. Requires EXPORT_IDENTIFIABLE permission." />
                        </label>
                        <label className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Checkbox
                            checked={nodeBinding.includeAnswers}
                            onCheckedChange={(checked) =>
                              setNodeBinding((prev) => ({
                                ...prev,
                                includeAnswers: checked === true,
                              }))
                            }
                          />
                          Include answers
                          <HelpTip text="Include the full text of student responses in the export." />
                        </label>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      Data source settings are only available for files.
                    </p>
                  )}

                  {/* Save and Delete buttons */}
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      onClick={() => void handleSaveNodeProperties()}
                      disabled={isSavingNode}
                    >
                      <Save className="mr-2 size-4" />
                      {isSavingNode ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      type="button"
                      variant="destructive"
                      onClick={() => void handleDeleteNode(selectedNode)}
                    >
                      <Trash2 className="mr-2 size-4" />
                      Delete
                    </Button>
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </section>
      </div>

      {/* ---- Footer: PackageBuildBar ---- */}
      <PackageBuildBar
        canExportIdentifiable={canExportIdentifiable}
        role={role}
        strictMode={strictMode}
        onStrictModeChange={setStrictMode}
        validationResult={validationResult}
        buildResult={buildResult}
        isValidating={isValidating}
        isBuilding={isBuilding}
        isDownloadingArtifact={isDownloadingArtifact}
        onValidate={handleValidateWorkspace}
        onBuild={() => void handleBuildWorkspace()}
        onDownload={() => void handleDownloadArtifact()}
      />
    </div>
  );
}
