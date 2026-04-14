'use client';

import {
  Plus,
  Trash2,
  Eye,
  Pencil,
  Layers,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { HelpTip } from '@/components/ui/help-tip';
import { type QuestionGroupInput } from '@/lib/assignment-template-api';
import { type Rubric } from '@/lib/rubric-api';

export type QuestionGroupPanelProps = {
  isRubricEnabled: boolean;
  isRubricsLoading: boolean;
  rubrics: Rubric[];
  rubricApplyId: string;
  onRubricApplyIdChange: (value: string) => void;
  onApplyRubricToSelected: () => void;
  onOpenQuickRubric: () => void;
  onOpenInlineRubricEditor: (rubricId: number | null | undefined) => void;
  onOpenRubricPreview: (rubricId: number | null | undefined) => void;
  showTips: boolean;
  questionGroups: QuestionGroupInput[];
  newGroupName: string;
  onNewGroupNameChange: (value: string) => void;
  onCreateGroup: () => void;
  ungroupedCount: number;
  activeSelectionCount: number;
  assignGroupKey: string;
  onAssignGroupKeyChange: (value: string) => void;
  selectedAssignGroup: QuestionGroupInput | null;
  questionCountByGroupKey: Map<string, number>;
  rubricById: Map<number, Rubric>;
  onUpdateQuestionGroup: (clientKey: string, patch: Partial<QuestionGroupInput>) => void;
  onRemoveQuestionGroup: (clientKey: string) => void;
  onAssignGroupToSelected: () => void;
};

export default function QuestionGroupPanel({
  isRubricEnabled,
  isRubricsLoading,
  rubrics,
  rubricApplyId,
  onRubricApplyIdChange,
  onApplyRubricToSelected,
  onOpenQuickRubric,
  onOpenInlineRubricEditor,
  onOpenRubricPreview,
  showTips,
  questionGroups,
  newGroupName,
  onNewGroupNameChange,
  onCreateGroup,
  ungroupedCount,
  activeSelectionCount,
  assignGroupKey,
  onAssignGroupKeyChange,
  selectedAssignGroup,
  questionCountByGroupKey,
  rubricById,
  onUpdateQuestionGroup,
  onRemoveQuestionGroup,
  onAssignGroupToSelected,
}: QuestionGroupPanelProps) {
  return (
    <aside className="rounded-sm border border-border bg-card p-4 space-y-4 xl:sticky xl:top-4 max-h-[calc(100vh-180px)] overflow-y-auto">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <h3 className="text-sm font-semibold text-foreground">Rubric Binding</h3>
          <HelpTip text="Attach rubric templates to manual questions. In HYBRID mode, questions marked AUTO should not have rubrics." />
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={onOpenQuickRubric}
        >
          <Plus className="mr-1 h-4 w-4" /> New Rubric
        </Button>
      </div>

      {!isRubricEnabled ? (
        <div className="rounded border border-border bg-muted/40 p-3 text-xs text-muted-foreground space-y-1">
          <p className="font-medium text-foreground">Rubrics disabled in AUTO mode</p>
          <p>Switch grading mode to MANUAL or HYBRID to attach rubrics.</p>
        </div>
      ) : (
        <>
          {isRubricsLoading ? (
            <p className="text-xs text-muted-foreground">Loading rubrics...</p>
          ) : (
            <div className="space-y-2">
              <Label>Rubric template</Label>
              <div className="grid grid-cols-[1fr_auto_auto] gap-2">
                <Select value={rubricApplyId} onValueChange={onRubricApplyIdChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select rubric" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__NONE__">No rubric</SelectItem>
                    {rubrics.map((rubric) => (
                      <SelectItem
                        key={rubric.id}
                        value={String(rubric.id)}
                        disabled={rubric.status !== 'ACTIVE'}
                      >
                        {rubric.title}
                        {rubric.status !== 'ACTIVE' ? ' (Archived)' : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="h-9 w-9"
                  disabled={rubricApplyId === '__NONE__'}
                  onClick={() =>
                    onOpenInlineRubricEditor(
                      rubricApplyId === '__NONE__' ? null : Number(rubricApplyId),
                    )
                  }
                >
                  <Pencil className="h-4 w-4" />
                  <span className="sr-only">Edit selected rubric</span>
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="h-9 w-9"
                  disabled={rubricApplyId === '__NONE__'}
                  onClick={() =>
                    onOpenRubricPreview(
                      rubricApplyId === '__NONE__' ? null : Number(rubricApplyId),
                    )
                  }
                >
                  <Eye className="h-4 w-4" />
                  <span className="sr-only">Preview selected rubric</span>
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Attach to selected questions. Use the eye icon to preview the selected template.
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 gap-2">
            <Button type="button" variant="outline" onClick={onApplyRubricToSelected}>
              Apply to Active/Selected Questions
            </Button>
            {showTips && (
              <p className="text-xs text-muted-foreground">
                Tip: select multiple questions on the left, then apply once.
              </p>
            )}
          </div>

          <div className="border-t border-border pt-3 space-y-3">
            <div className="flex items-center gap-1.5">
              <h4 className="text-sm font-semibold text-foreground">Group Manager</h4>
              <HelpTip text="Use groups when multiple questions should share the same rubric. Group rubrics are inherited by questions that do not have a direct rubric." />
            </div>

            <div className="grid grid-cols-[1fr_auto] gap-2">
              <Input
                placeholder="New group name"
                value={newGroupName}
                onChange={(e) => onNewGroupNameChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    onCreateGroup();
                  }
                }}
              />
              <Button type="button" variant="outline" onClick={onCreateGroup}>
                <Plus className="mr-1 h-4 w-4" /> Add
              </Button>
            </div>

            <div className="rounded border border-border bg-muted/30 p-2 text-xs text-muted-foreground">
              {questionGroups.length} group(s), {ungroupedCount} ungrouped question(s), applying to {activeSelectionCount} selected question(s).
            </div>

            <div className="grid grid-cols-1 gap-2">
              <Select value={assignGroupKey} onValueChange={onAssignGroupKeyChange}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Assign selected to group" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__NONE__">No group</SelectItem>
                  {questionGroups.map((group) => (
                    <SelectItem key={group.clientKey} value={group.clientKey}>
                      {group.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {questionGroups.length === 0 && (
              <p className="text-xs text-muted-foreground">
                No groups yet. Create one to share rubric settings across questions.
              </p>
            )}

            {questionGroups.length > 0 && selectedAssignGroup && (
              <div className="rounded border border-border p-2 space-y-2">
                <div className="flex items-center gap-2">
                  <Input
                    value={selectedAssignGroup.name}
                    onChange={(e) =>
                      onUpdateQuestionGroup(selectedAssignGroup.clientKey, {
                        name: e.target.value,
                      })
                    }
                    placeholder="Group name"
                  />
                  <span className="rounded bg-muted px-2 py-1 text-[10px] text-muted-foreground whitespace-nowrap">
                    {questionCountByGroupKey.get(selectedAssignGroup.clientKey) ?? 0}{' '}
                    question(s)
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive"
                    onClick={() => onRemoveQuestionGroup(selectedAssignGroup.clientKey)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>

                <div className="grid grid-cols-[1fr_auto_auto] gap-2">
                  <Select
                    value={
                      selectedAssignGroup.rubricId != null
                        ? String(selectedAssignGroup.rubricId)
                        : '__NONE__'
                    }
                    onValueChange={(value) =>
                      onUpdateQuestionGroup(selectedAssignGroup.clientKey, {
                        rubricId: value === '__NONE__' ? null : Number(value),
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Group rubric" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__NONE__">No group rubric</SelectItem>
                      {rubrics.map((rubricOption) => (
                        <SelectItem
                          key={rubricOption.id}
                          value={String(rubricOption.id)}
                          disabled={rubricOption.status !== 'ACTIVE'}
                        >
                          {rubricOption.title}
                          {rubricOption.status !== 'ACTIVE' ? ' (Archived)' : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="h-9 w-9"
                    disabled={selectedAssignGroup.rubricId == null}
                    onClick={() => onOpenInlineRubricEditor(selectedAssignGroup.rubricId)}
                  >
                    <Pencil className="h-4 w-4" />
                    <span className="sr-only">Edit group rubric</span>
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="h-9 w-9"
                    disabled={selectedAssignGroup.rubricId == null}
                    onClick={() => onOpenRubricPreview(selectedAssignGroup.rubricId)}
                  >
                    <Eye className="h-4 w-4" />
                    <span className="sr-only">Preview group rubric</span>
                  </Button>
                </div>

                <p className="text-xs text-muted-foreground">
                  {selectedAssignGroup.rubricId
                    ? `Using rubric: ${
                        rubricById.get(selectedAssignGroup.rubricId)?.title ??
                        'Unavailable'
                      }`
                    : 'No rubric attached to this group'}
                </p>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={onAssignGroupToSelected}
                >
                  <Layers className="mr-1 h-4 w-4" />
                  Apply Group To Active/Selected
                </Button>
              </div>
            )}
          </div>
        </>
      )}
    </aside>
  );
}
