'use client';

import { memo, useState, useRef, useEffect } from 'react';
import {
  Plus,
  FolderPlus,
  GripVertical,
  AlertCircle,
  FileText,
  ChevronDown,
  ChevronRight,
  ArrowLeft,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import type { QuestionInput, QuestionGroupInput, QuestionKind } from '@/lib/assessment-api';
import { cn } from '@/lib/utils';

function formatQuestionKind(kind: QuestionKind): string {
  switch (kind) {
    case 'MULTIPLE_CHOICE':
      return 'MCQ';
    case 'SHORT_ANSWER':
      return 'SA';
    case 'NUMBER_SCALE':
      return 'NS';
    case 'MOOD_METER':
      return 'MM';
    case 'FILE_UPLOAD':
      return 'FU';
    default:
      return kind;
  }
}

function questionTypeColor(kind: QuestionKind): string {
  switch (kind) {
    case 'MULTIPLE_CHOICE':
      return 'text-blue-600 dark:text-blue-400';
    case 'SHORT_ANSWER':
      return 'text-green-600 dark:text-green-400';
    case 'NUMBER_SCALE':
      return 'text-amber-600 dark:text-amber-400';
    case 'MOOD_METER':
      return 'text-purple-600 dark:text-purple-400';
    case 'FILE_UPLOAD':
      return 'text-rose-600 dark:text-rose-400';
    default:
      return 'text-muted-foreground';
  }
}

type StructureRailProps = {
  questions: QuestionInput[];
  questionGroups: QuestionGroupInput[];
  selectedIndex: number;
  onSelectQuestion: (index: number) => void;
  onBackToEditor?: () => void;
  onAddQuestion: () => void;
  onAddGroup: (name?: string) => void;
  onRenameGroup: (clientKey: string, newName: string) => void;
  onAssignGroup: (questionIndex: number, groupClientKey: string | undefined) => void;
  draggingQuestionIndex: number | null;
  dragOverQuestionIndex: number | null;
  onDragStart: (index: number) => void;
  onDragOver: (index: number) => void;
  onDrop: (from: number, to: number) => void;
  onDragEnd: () => void;
  groupByKey: Map<string, QuestionGroupInput>;
  highlightQuestionListSignal?: number;
};

function isQuestionValid(q: QuestionInput): boolean {
  if (!q.prompt.trim()) return false;
  if (q.type === 'MULTIPLE_CHOICE') {
    const choices = q.data?.choices;
    if (!choices || choices.length < 2) return false;
    if (choices.some((c) => !c.prompt.trim())) return false;
  }
  if (q.type === 'NUMBER_SCALE') {
    const min = q.data?.min ?? 0;
    const max = q.data?.max ?? 0;
    if (min >= max) return false;
  }
  return true;
}

function StructureRail({
  questions,
  questionGroups,
  selectedIndex,
  onSelectQuestion,
  onBackToEditor,
  onAddQuestion,
  onAddGroup,
  onRenameGroup,
  onAssignGroup,
  draggingQuestionIndex,
  dragOverQuestionIndex,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
  groupByKey,
  highlightQuestionListSignal,
}: StructureRailProps) {
  const totalPoints = questions.reduce((sum, q) => sum + (q.maxPoints || 0), 0);
  const ungroupedQuestions = questions
    .map((q, i) => ({ question: q, globalIndex: i }))
    .filter(({ question }) => !question.groupClientKey);

  // Collapsible state for groups
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [collapsedUngrouped, setCollapsedUngrouped] = useState(false);
  // Track which group zone is being hovered for visual feedback
  const [dragOverGroup, setDragOverGroup] = useState<string | null>(null);
  // Inline group renaming
  const [editingGroupKey, setEditingGroupKey] = useState<string | null>(null);
  const [editingGroupName, setEditingGroupName] = useState('');
  // New group dialog
  const [newGroupDialogOpen, setNewGroupDialogOpen] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [highlightAddQuestion, setHighlightAddQuestion] = useState(false);
  const newGroupInputRef = useRef<HTMLInputElement>(null);
  const addQuestionButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (newGroupDialogOpen) {
      setTimeout(() => newGroupInputRef.current?.focus(), 100);
    }
  }, [newGroupDialogOpen]);

  useEffect(() => {
    if (!highlightQuestionListSignal) return;
    addQuestionButtonRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setHighlightAddQuestion(true);
    const timeout = window.setTimeout(() => setHighlightAddQuestion(false), 1800);
    return () => window.clearTimeout(timeout);
  }, [highlightQuestionListSignal]);
  // "ungrouped" is tracked as "__UNGROUPED__"
  const UNGROUPED_KEY = '__UNGROUPED__';

  const startRenameGroup = (clientKey: string, currentName: string) => {
    setEditingGroupKey(clientKey);
    setEditingGroupName(currentName);
  };

  const commitRename = () => {
    if (editingGroupKey && editingGroupName.trim()) {
      onRenameGroup(editingGroupKey, editingGroupName.trim());
    }
    setEditingGroupKey(null);
    setEditingGroupName('');
  };

  const toggleGroup = (key: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleGroupDragOver = (e: React.DragEvent, groupKey: string) => {
    e.preventDefault();
    if (draggingQuestionIndex !== null) {
      setDragOverGroup(groupKey);
    }
  };

  const handleGroupDragLeave = () => {
    setDragOverGroup(null);
  };

  const handleGroupDrop = (e: React.DragEvent, groupClientKey: string | undefined) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverGroup(null);
    if (draggingQuestionIndex !== null) {
      onAssignGroup(draggingQuestionIndex, groupClientKey);
      onDragEnd();
    }
  };

  const renderQuestionRow = (q: QuestionInput, globalIndex: number) => {
    const isActive = selectedIndex === globalIndex;
    const valid = isQuestionValid(q);

    const isDragTarget = dragOverQuestionIndex === globalIndex && draggingQuestionIndex !== globalIndex;

    return (
      <div key={`q-${globalIndex}`} className="relative">
        {/* Insertion line above this question when dragging */}
        {isDragTarget && (
          <div className="absolute -top-0.5 left-2 right-2 h-0.5 bg-primary rounded-full z-10" />
        )}
        <button
          type="button"
          data-question-row="true"
          onClick={() => onSelectQuestion(globalIndex)}
          className={cn(
            'w-full group flex items-center gap-2.5 p-2 rounded-md transition-colors text-left relative border',
            isActive
              ? 'bg-accent border-border shadow-sm'
              : 'hover:bg-accent/50 border-transparent',
            isDragTarget && 'border-primary/40 bg-primary/5',
            draggingQuestionIndex === globalIndex && 'opacity-40',
          )}
        onDragOver={(e) => {
          e.preventDefault();
          if (draggingQuestionIndex !== null && draggingQuestionIndex !== globalIndex) {
            onDragOver(globalIndex);
          }
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (draggingQuestionIndex !== null) {
            onDrop(draggingQuestionIndex, globalIndex);
          }
          onDragEnd();
        }}
        onDragEnd={onDragEnd}
      >
        {isActive && (
          <div className="absolute left-0 top-2 bottom-2 w-0.5 bg-primary rounded-r-sm" />
        )}

        {/* Grip handle — centered vertically */}
        <span
          role="button"
          tabIndex={0}
          draggable
          aria-label={`Drag question ${globalIndex + 1}`}
          className="flex-shrink-0 cursor-grab text-muted-foreground/40 hover:text-muted-foreground active:cursor-grabbing transition-colors self-center"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              e.stopPropagation();
            }
          }}
          onDragStart={(e) => {
            e.stopPropagation();
            const row = e.currentTarget.closest(
              '[data-question-row="true"]',
            ) as HTMLElement | null;
            if (row) e.dataTransfer.setDragImage(row, 24, 18);
            onDragStart(globalIndex);
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', String(globalIndex));
          }}
          onDragEnd={(e) => {
            e.stopPropagation();
            onDragEnd();
          }}
        >
          <GripVertical className="h-3.5 w-3.5" />
        </span>

        {/* Question number badge */}
        <span
          className={cn(
            'flex-shrink-0 text-[10px] font-bold font-mono w-5 h-5 flex items-center justify-center rounded',
            isActive
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground',
          )}
        >
          {globalIndex + 1}
        </span>

        {/* Question info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-1 mb-0.5">
            <span
              className={cn(
                'text-[9px] font-bold uppercase tracking-wider',
                questionTypeColor(q.type),
              )}
            >
              {formatQuestionKind(q.type)}
            </span>
            <div className="flex items-center gap-1">
              {!valid && (
                <AlertCircle className="h-3 w-3 text-amber-500 dark:text-amber-400" />
              )}
              <span className="text-[9px] font-mono text-muted-foreground font-medium">
                {q.maxPoints}pt
              </span>
            </div>
          </div>
          <p
            className={cn(
              'text-xs truncate leading-tight',
              isActive ? 'text-foreground font-medium' : 'text-muted-foreground',
            )}
          >
            {q.prompt.trim() || (
              <span className="italic opacity-50">No prompt text</span>
            )}
          </p>
        </div>
      </button>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      <div className="lg:hidden p-3 border-b border-border bg-card flex items-center justify-between">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onBackToEditor}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
          Structure
        </span>
      </div>

      {/* Header */}
      <div className="p-3 border-b border-border bg-card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
            Structure
          </h2>
          <span className="text-[10px] font-medium text-muted-foreground">
            {questions.length} question{questions.length !== 1 ? 's' : ''}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <Button
            ref={addQuestionButtonRef}
            type="button"
            size="sm"
            onClick={onAddQuestion}
            className={cn(
              'gap-1.5 text-sm transition-shadow',
              highlightAddQuestion && 'ring-2 ring-amber-400/70 ring-offset-2 ring-offset-card',
            )}
          >
            <Plus className="h-4 w-4" />
            Question
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              setNewGroupName('');
              setNewGroupDialogOpen(true);
            }}
            className="gap-1.5 text-sm"
          >
            <FolderPlus className="h-4 w-4" />
            Group
          </Button>
        </div>
      </div>

      {/* Question tree */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {/* Ungrouped section */}
        {(ungroupedQuestions.length > 0 || questionGroups.length > 0) && (
          <div
            onDragOver={(e) => handleGroupDragOver(e, UNGROUPED_KEY)}
            onDragLeave={handleGroupDragLeave}
            onDrop={(e) => handleGroupDrop(e, undefined)}
            className={cn(
              'rounded-md transition-colors',
              dragOverGroup === UNGROUPED_KEY && draggingQuestionIndex !== null && 'bg-primary/5 ring-1 ring-primary/30',
            )}
          >
            {questionGroups.length > 0 && (
              <button
                type="button"
                onClick={() => setCollapsedUngrouped(!collapsedUngrouped)}
                className="flex items-center gap-1.5 px-1 py-1 w-full text-left group hover:bg-accent/30 rounded transition-colors"
              >
                {collapsedUngrouped ? (
                  <ChevronRight className="h-3 w-3 text-muted-foreground/60" />
                ) : (
                  <ChevronDown className="h-3 w-3 text-muted-foreground/60" />
                )}
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
                  Ungrouped
                </span>
                <span className="text-[9px] font-medium text-muted-foreground/50 ml-auto">
                  {ungroupedQuestions.length}
                </span>
              </button>
            )}
            {!collapsedUngrouped && (
              <div className={cn('space-y-0.5', questionGroups.length > 0 && 'pl-2 ml-1.5 border-l border-border')}>
                {ungroupedQuestions.map(({ question, globalIndex }) =>
                  renderQuestionRow(question, globalIndex),
                )}
              </div>
            )}
          </div>
        )}

        {/* Grouped sections */}
        {questionGroups.map((group) => {
          const groupQuestions = questions
            .map((q, i) => ({ question: q, globalIndex: i }))
            .filter(({ question }) => question.groupClientKey === group.clientKey);
          const isCollapsed = collapsedGroups.has(group.clientKey);

          return (
            <div
              key={group.clientKey}
              onDragOver={(e) => handleGroupDragOver(e, group.clientKey)}
              onDragLeave={handleGroupDragLeave}
              onDrop={(e) => handleGroupDrop(e, group.clientKey)}
              className={cn(
                'rounded-md transition-colors',
                dragOverGroup === group.clientKey && draggingQuestionIndex !== null && 'bg-primary/5 ring-1 ring-primary/30',
              )}
            >
              <div className="flex items-center gap-1.5 px-1 py-1 w-full">
                <button
                  type="button"
                  onClick={() => toggleGroup(group.clientKey)}
                  className="flex-shrink-0 hover:bg-accent/30 rounded p-0.5 transition-colors"
                >
                  {isCollapsed ? (
                    <ChevronRight className="h-3 w-3 text-muted-foreground/60" />
                  ) : (
                    <ChevronDown className="h-3 w-3 text-muted-foreground/60" />
                  )}
                </button>

                {editingGroupKey === group.clientKey ? (
                  <input
                    type="text"
                    value={editingGroupName}
                    onChange={(e) => setEditingGroupName(e.target.value)}
                    onBlur={commitRename}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') commitRename();
                      if (e.key === 'Escape') { setEditingGroupKey(null); setEditingGroupName(''); }
                    }}
                    autoFocus
                    className="flex-1 min-w-0 text-[10px] font-bold uppercase tracking-tight bg-background border border-border rounded px-1.5 py-0.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                ) : (
                  <span
                    onDoubleClick={() => startRenameGroup(group.clientKey, group.name)}
                    className="flex-1 min-w-0 text-[10px] font-bold uppercase tracking-tight text-muted-foreground cursor-text truncate"
                    title="Double-click to rename"
                  >
                    {group.name}
                  </span>
                )}

                <span className="text-[9px] font-medium text-muted-foreground/50 flex-shrink-0">
                  {groupQuestions.length}
                </span>
              </div>

              {!isCollapsed && (
                <div className="pl-2 border-l border-border ml-1.5 space-y-0.5">
                  {groupQuestions.map(({ question, globalIndex }) =>
                    renderQuestionRow(question, globalIndex),
                  )}
                  {groupQuestions.length === 0 && (
                    <p className="text-[10px] text-muted-foreground/50 py-2 px-2 italic">
                      Drop questions here
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {/* Empty state */}
        {questions.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <div className="w-10 h-10 bg-muted rounded-md flex items-center justify-center mb-3 text-muted-foreground">
              <FileText className="h-5 w-5" />
            </div>
            <p className="text-xs font-medium text-foreground">No questions added</p>
            <p className="text-[10px] text-muted-foreground mt-1 leading-relaxed">
              Create the first question to begin building this assessment.
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-border bg-muted/30">
        <div className="flex items-center justify-between text-xs font-bold text-muted-foreground uppercase tracking-widest">
          <span>Total Points</span>
          <span className="font-mono text-foreground text-sm">{totalPoints}</span>
        </div>
      </div>

      {/* New Group Dialog */}
      <Dialog open={newGroupDialogOpen} onOpenChange={setNewGroupDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Create Question Group</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-2">
              <Label htmlFor="new-group-name">Group Name</Label>
              <Input
                ref={newGroupInputRef}
                id="new-group-name"
                placeholder="e.g., Memory & Perception"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    onAddGroup(newGroupName || undefined);
                    setNewGroupDialogOpen(false);
                  }
                }}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setNewGroupDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={() => {
                onAddGroup(newGroupName || undefined);
                setNewGroupDialogOpen(false);
              }}
            >
              Create Group
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default memo(StructureRail);
