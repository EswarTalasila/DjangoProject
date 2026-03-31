'use client';

import {
  ChevronsDownUp,
  ChevronsUpDown,
  ChevronDown,
  ChevronRight,
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
  Trash2,
  Users,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { PackageNode } from '@/lib/package-api';

type AddCursor = {
  parentId: 'ROOT' | number;
  kind: 'FOLDER' | 'FILE';
  label: string;
};

function FileIcon({ node }: { node: PackageNode }) {
  if (node.nodeType === 'FOLDER') return null;
  switch (node.datasetBinding) {
    case 'ROSTER':
      return <Users className="size-4 text-green-500" />;
    case 'COURSE_SUBMISSIONS':
      return <FileText className="size-4 text-purple-500" />;
    default:
      return <File className="size-4 text-sky-500" />;
  }
}

function sortNodes(nodes: PackageNode[]) {
  return [...nodes].sort((a, b) => {
    if (a.orderIndex !== b.orderIndex) return a.orderIndex - b.orderIndex;
    return a.id - b.id;
  });
}

export type PackageTreeViewProps = {
  workspaceNodes: PackageNode[];
  childrenMap: Map<string, PackageNode[]>;
  rootNodes: PackageNode[];
  selectedNodeId: number | null;
  expandedFolders: Set<number>;
  editingNodeId: number | null;
  editingLabel: string;
  addCursor: AddCursor | null;
  draggedNodeId: number | null;
  dropTargetId: number | 'ROOT' | null;
  isSavingNode: boolean;
  onSelectNode: (node: PackageNode) => void;
  onToggleFolder: (nodeId: number) => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  onStartRename: (node: PackageNode) => void;
  onEditingLabelChange: (value: string) => void;
  onRename: (node: PackageNode) => void;
  onCancelRename: () => void;
  onStartAdd: (parentId: 'ROOT' | number, kind: 'FOLDER' | 'FILE') => void;
  onAddCursorChange: (updater: (prev: AddCursor | null) => AddCursor | null) => void;
  onAddNode: () => void;
  onCancelAdd: () => void;
  onMoveNode: (node: PackageNode, direction: -1 | 1) => void;
  onDropNode: (movedId: number, targetParentId: number | null) => void;
  onDeleteNode: (node: PackageNode) => void;
  onDraggedNodeIdChange: (id: number | null) => void;
  onDropTargetIdChange: (id: number | 'ROOT' | null) => void;
};

export default function PackageTreeView({
  workspaceNodes,
  childrenMap,
  rootNodes,
  selectedNodeId,
  expandedFolders,
  editingNodeId,
  editingLabel,
  addCursor,
  draggedNodeId,
  dropTargetId,
  isSavingNode,
  onSelectNode,
  onToggleFolder,
  onExpandAll,
  onCollapseAll,
  onStartRename,
  onEditingLabelChange,
  onRename,
  onCancelRename,
  onStartAdd,
  onAddCursorChange,
  onAddNode,
  onCancelAdd,
  onMoveNode,
  onDropNode,
  onDeleteNode,
  onDraggedNodeIdChange,
  onDropTargetIdChange,
}: PackageTreeViewProps) {
  function renderNode(node: PackageNode, depth: number) {
    const isFolder = node.nodeType === 'FOLDER';
    const isExpanded = expandedFolders.has(node.id);
    const children = childrenMap.get(String(node.id)) ?? [];
    const siblings = sortNodes(
      workspaceNodes.filter(
        (candidate) => candidate.parentId === node.parentId,
      ),
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
          onDraggedNodeIdChange(node.id);
        }}
        onDragEnd={() => {
          onDraggedNodeIdChange(null);
          onDropTargetIdChange(null);
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
              onDropTargetIdChange(node.id);
            }
          }}
          onDragLeave={() => {
            if (dropTargetId === node.id) onDropTargetIdChange(null);
          }}
          onDrop={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDropTargetIdChange(null);
            if (draggedNodeId != null && isFolder) {
              onDropNode(draggedNodeId, node.id);
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
                  onToggleFolder(node.id);
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
              onClick={() => onSelectNode(node)}
              className="truncate font-medium text-foreground hover:underline text-left"
            >
              {isEditing ? (
                <Input
                  value={editingLabel}
                  onChange={(event) => onEditingLabelChange(event.target.value)}
                  onClick={(event) => {
                    event.stopPropagation();
                  }}
                  className="h-7 w-52"
                  autoFocus
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      onRename(node);
                    }
                    if (event.key === 'Escape') {
                      onCancelRename();
                    }
                  }}
                  onBlur={() => onRename(node)}
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
                onStartRename(node);
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
                onMoveNode(node, -1);
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
                onMoveNode(node, 1);
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
                    onStartAdd(node.id, 'FOLDER');
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
                    onStartAdd(node.id, 'FILE');
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
                onDeleteNode(node);
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
                  onAddCursorChange(
                    (prev) =>
                      prev && {
                        ...prev,
                        label: event.target.value,
                      },
                  )
                }
                onKeyDown={(event) => {
                  if (event.key === 'Enter') onAddNode();
                  if (event.key === 'Escape') onCancelAdd();
                }}
                placeholder={`New ${addCursor?.kind.toLowerCase()}`}
                className="h-7"
              />
              <Button
                type="button"
                size="sm"
                onClick={onAddNode}
              >
                Add
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={onCancelAdd}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <section className="flex flex-col rounded-sm border border-border bg-card overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center gap-1 border-b border-border px-3 py-2">
        <span className="text-sm font-semibold text-foreground mr-auto">
          Explorer
        </span>
        <button
          type="button"
          className="rounded p-1.5 text-muted-foreground hover:bg-accent"
          onClick={() => onStartAdd('ROOT', 'FOLDER')}
          title="New folder at root"
        >
          <FolderPlus className="size-4" />
        </button>
        <button
          type="button"
          className="rounded p-1.5 text-muted-foreground hover:bg-accent"
          onClick={() => onStartAdd('ROOT', 'FILE')}
          title="New file at root"
        >
          <FilePlus className="size-4" />
        </button>
        <button
          type="button"
          className="rounded p-1.5 text-muted-foreground hover:bg-accent"
          onClick={onExpandAll}
          title="Expand all"
        >
          <ChevronsUpDown className="size-4" />
        </button>
        <button
          type="button"
          className="rounded p-1.5 text-muted-foreground hover:bg-accent"
          onClick={onCollapseAll}
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
                onAddCursorChange((prev) =>
                  prev ? { ...prev, label: event.target.value } : prev,
                )
              }
              onKeyDown={(event) => {
                if (event.key === 'Enter') onAddNode();
                if (event.key === 'Escape') onCancelAdd();
              }}
              placeholder={`New ${addCursor.kind.toLowerCase()} at root`}
              className="h-7"
            />
            <Button
              type="button"
              size="sm"
              onClick={onAddNode}
            >
              Add
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onCancelAdd}
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

        {/* Root drop zone -- appears during drag */}
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
              onDropTargetIdChange('ROOT');
            }}
            onDragLeave={() => {
              if (dropTargetId === 'ROOT') onDropTargetIdChange(null);
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onDropTargetIdChange(null);
              if (draggedNodeId != null) {
                onDropNode(draggedNodeId, null);
              }
            }}
          >
            Drop here to move to root
          </div>
        )}
      </div>
    </section>
  );
}
