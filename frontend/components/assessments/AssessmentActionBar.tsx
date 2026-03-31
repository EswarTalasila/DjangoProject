'use client';

import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { type Rubric } from '@/lib/rubric-api';
import RubricQuickBuilderDrawer from './RubricQuickBuilderDrawer';
import RubricTemplatePreviewDrawer from './RubricTemplatePreviewDrawer';

export type AssessmentActionBarProps = {
  mode: 'create' | 'edit';
  isSubmitting: boolean;
  onCancel: () => void;
  // Rubric drawers
  isQuickRubricOpen: boolean;
  onQuickRubricOpenChange: (open: boolean) => void;
  onQuickRubricCreated: (rubric: Rubric) => void;
  isQuickRubricEditOpen: boolean;
  onQuickRubricEditOpenChange: (open: boolean) => void;
  quickEditRubricId: number | null;
  onQuickRubricSaved: (rubric: Rubric) => void;
  isRubricPreviewOpen: boolean;
  onRubricPreviewOpenChange: (open: boolean) => void;
  previewRubricId: number | null;
  onOpenInlineRubricEditor: (rubricId: number | null | undefined) => void;
  onOpenFullRubricEditor: (rubricId?: number | null) => void;
};

export default function AssessmentActionBar({
  mode,
  isSubmitting,
  onCancel,
  isQuickRubricOpen,
  onQuickRubricOpenChange,
  onQuickRubricCreated,
  isQuickRubricEditOpen,
  onQuickRubricEditOpenChange,
  quickEditRubricId,
  onQuickRubricSaved,
  isRubricPreviewOpen,
  onRubricPreviewOpenChange,
  previewRubricId,
  onOpenInlineRubricEditor,
  onOpenFullRubricEditor,
}: AssessmentActionBarProps) {
  return (
    <>
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {mode === 'create' ? 'Create Assessment' : 'Save Changes'}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
      </div>

      <RubricQuickBuilderDrawer
        open={isQuickRubricOpen}
        onOpenChange={onQuickRubricOpenChange}
        mode="create"
        onCreated={onQuickRubricCreated}
        onOpenFullEditor={onOpenFullRubricEditor}
      />
      <RubricQuickBuilderDrawer
        open={isQuickRubricEditOpen}
        onOpenChange={onQuickRubricEditOpenChange}
        mode="edit"
        rubricId={quickEditRubricId}
        onSaved={onQuickRubricSaved}
        onOpenFullEditor={onOpenFullRubricEditor}
      />
      <RubricTemplatePreviewDrawer
        open={isRubricPreviewOpen}
        onOpenChange={onRubricPreviewOpenChange}
        rubricId={previewRubricId}
        onEditRubric={onOpenInlineRubricEditor}
        onOpenFullEditor={onOpenFullRubricEditor}
      />
    </>
  );
}
