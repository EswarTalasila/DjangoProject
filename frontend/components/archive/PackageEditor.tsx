'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  Save,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { StatusBadge } from '@/components/ui/status-badge';
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
import PackageTreeView from './PackageTreeView';
import PackageNodeInspector from './PackageNodeInspector';
import PackageBuildPanel from './PackageBuildPanel';

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
  const [includeMetadataFiles, setIncludeMetadataFiles] = useState(true);
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
  const [deleteTargetNode, setDeleteTargetNode] = useState<PackageNode | null>(
    null,
  );

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
    setIsSavingNode(true);
    try {
      await deleteNode(workspace.id, node.id);
      setSelectedNodeId((prev) => (prev === node.id ? null : prev));
      setDeleteTargetNode(null);
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
          toast.success('Package is ready to build!');
        } else {
          const n = result.violations.length;
          toast.error(
            `Found ${n} ${n === 1 ? 'problem' : 'problems'} — see details below.`,
          );
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
        includeMetadataFiles,
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
        <PackageTreeView
          workspaceNodes={workspace.nodes}
          childrenMap={childrenMap}
          rootNodes={rootNodes}
          selectedNodeId={selectedNodeId}
          expandedFolders={expandedFolders}
          editingNodeId={editingNodeId}
          editingLabel={editingLabel}
          addCursor={addCursor}
          draggedNodeId={draggedNodeId}
          dropTargetId={dropTargetId}
          isSavingNode={isSavingNode}
          onSelectNode={selectNode}
          onToggleFolder={toggleFolder}
          onExpandAll={expandAll}
          onCollapseAll={collapseAll}
          onStartRename={startRename}
          onEditingLabelChange={setEditingLabel}
          onRename={(node) => void handleRename(node)}
          onCancelRename={() => setEditingNodeId(null)}
          onStartAdd={startAdd}
          onAddCursorChange={setAddCursor}
          onAddNode={() => void handleAddNode()}
          onCancelAdd={cancelAdd}
          onMoveNode={(node, dir) => void handleMoveNode(node, dir)}
          onDropNode={(movedId, targetParentId) => void handleDropNode(movedId, targetParentId)}
          onDeleteNode={setDeleteTargetNode}
          onDraggedNodeIdChange={setDraggedNodeId}
          onDropTargetIdChange={setDropTargetId}
        />

        {/* Right pane: Catalog + Properties tabs */}
        <PackageNodeInspector
          workspace={workspace}
          selectedNode={selectedNode}
          courses={courses}
          canExportIdentifiable={canExportIdentifiable}
          nodeLabel={nodeLabel}
          onNodeLabelChange={setNodeLabel}
          nodeOrderIndex={nodeOrderIndex}
          onNodeOrderIndexChange={setNodeOrderIndex}
          nodeParentId={nodeParentId}
          onNodeParentIdChange={setNodeParentId}
          nodeBinding={nodeBinding}
          onNodeBindingChange={setNodeBinding}
          isSavingNode={isSavingNode}
          onSaveNodeProperties={() => void handleSaveNodeProperties()}
          onDeleteNode={setDeleteTargetNode}
          onAddFromCatalog={handleAddFromCatalog}
        />
      </div>

      {/* ---- Footer: Build bar + delete dialog ---- */}
      <PackageBuildPanel
        canExportIdentifiable={canExportIdentifiable}
        role={role}
        strictMode={strictMode}
        onStrictModeChange={setStrictMode}
        includeMetadataFiles={includeMetadataFiles}
        onIncludeMetadataFilesChange={setIncludeMetadataFiles}
        validationResult={validationResult}
        buildResult={buildResult}
        isValidating={isValidating}
        isBuilding={isBuilding}
        isDownloadingArtifact={isDownloadingArtifact}
        onValidate={handleValidateWorkspace}
        onBuild={() => void handleBuildWorkspace()}
        onDownload={() => void handleDownloadArtifact()}
        deleteTargetNode={deleteTargetNode}
        onDeleteTargetNodeChange={setDeleteTargetNode}
        isSavingNode={isSavingNode}
        onDeleteNode={(node) => void handleDeleteNode(node)}
      />
    </div>
  );
}
