'use client';

import {
  ArrowLeft,
  Loader2,
  FileText,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/ui/status-badge';
import { cn } from '@/lib/utils';

type AssessmentStudioHeaderProps = {
  title: string;
  onTitleChange: (title: string) => void;
  titleError: string | null;
  status: string;
  mode: 'create' | 'edit';
  isSubmitting: boolean;
  onSave: () => void;
  onCancel: () => void;
};

export default function AssessmentStudioHeader({
  title,
  onTitleChange,
  titleError,
  status,
  mode,
  isSubmitting,
  onSave,
  onCancel,
}: AssessmentStudioHeaderProps) {
  return (
    <header className="h-14 border-b border-border bg-card flex items-center justify-between px-4 gap-4 shrink-0">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0"
          onClick={onCancel}
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="sr-only">Back to assessments</span>
        </Button>

        <div className="w-8 h-8 bg-primary rounded-md flex items-center justify-center text-primary-foreground shrink-0">
          <FileText className="h-4 w-4" />
        </div>

        <div className="flex flex-col min-w-0 flex-1">
          <input
            type="text"
            value={title}
            onChange={(e) => onTitleChange(e.target.value)}
            className={cn(
              'bg-transparent border-none p-0 text-sm font-semibold text-foreground focus:outline-none focus:ring-0 w-full truncate placeholder:text-muted-foreground',
              titleError && 'text-destructive',
            )}
            placeholder="Untitled Assessment"
          />
          <div className="flex items-center gap-2 mt-0.5">
            {mode === 'edit' && (
              <StatusBadge status={status || 'ACTIVE'} className="text-[10px]" />
            )}
            {mode === 'create' && (
              <StatusBadge status="DRAFT" className="text-[10px]" />
            )}
            {titleError && (
              <span className="text-[10px] text-destructive font-medium">
                {titleError}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onCancel}
          className="hidden sm:inline-flex"
        >
          Cancel
        </Button>
        <Button
          type="submit"
          size="sm"
          disabled={isSubmitting}
          onClick={onSave}
        >
          {isSubmitting && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
          {mode === 'create' ? 'Create' : 'Save Changes'}
        </Button>
      </div>
    </header>
  );
}
