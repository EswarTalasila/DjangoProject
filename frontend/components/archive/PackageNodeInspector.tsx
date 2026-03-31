'use client';

import { Save, Trash2 } from 'lucide-react';

import DataCatalog from '@/components/archive/DataCatalog';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { CourseSummary } from '@/lib/course-api';
import type { DatasetBinding, PackageNode, PackageWorkspace } from '@/lib/package-api';

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
];

const NONE_SELECT = '__ROOT__';

export type PackageNodeInspectorProps = {
  workspace: PackageWorkspace;
  selectedNode: PackageNode | null;
  courses: CourseSummary[];
  canExportIdentifiable: boolean;
  nodeLabel: string;
  onNodeLabelChange: (value: string) => void;
  nodeOrderIndex: string;
  onNodeOrderIndexChange: (value: string) => void;
  nodeParentId: string;
  onNodeParentIdChange: (value: string) => void;
  nodeBinding: NodeBindingForm;
  onNodeBindingChange: (updater: (prev: NodeBindingForm) => NodeBindingForm) => void;
  isSavingNode: boolean;
  onSaveNodeProperties: () => void;
  onDeleteNode: (node: PackageNode) => void;
  onAddFromCatalog: (config: {
    label: string;
    datasetBinding: DatasetBinding;
    bindingCourseId: number | null;
    sourceType?: 'LIVE' | 'SNAPSHOT';
    snapshotId?: number | null;
  }) => void;
};

export default function PackageNodeInspector({
  workspace,
  selectedNode,
  courses,
  canExportIdentifiable,
  nodeLabel,
  onNodeLabelChange,
  nodeOrderIndex,
  onNodeOrderIndexChange,
  nodeParentId,
  onNodeParentIdChange,
  nodeBinding,
  onNodeBindingChange,
  isSavingNode,
  onSaveNodeProperties,
  onDeleteNode,
  onAddFromCatalog,
}: PackageNodeInspectorProps) {
  return (
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
            onAddItem={onAddFromCatalog}
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
                    onChange={(event) => onNodeLabelChange(event.target.value)}
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
                      onNodeOrderIndexChange(event.target.value)
                    }
                  />
                </div>
                <div className="space-y-1">
                  <Label className="flex items-center gap-1">
                    Parent
                    <HelpTip text="The folder this item belongs to." />
                  </Label>
                  <Select value={nodeParentId} onValueChange={onNodeParentIdChange}>
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
                          onNodeBindingChange((prev) => ({
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
                          onNodeBindingChange((prev) => ({
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
                          onNodeBindingChange((prev) => ({
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
                          onNodeBindingChange((prev) => ({
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
                          onNodeBindingChange((prev) => ({
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
                  onClick={onSaveNodeProperties}
                  disabled={isSavingNode}
                >
                  <Save className="mr-2 size-4" />
                  {isSavingNode ? 'Saving...' : 'Save'}
                </Button>
                <Button
                  type="button"
                  variant="destructive"
                  onClick={() => onDeleteNode(selectedNode)}
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
  );
}
