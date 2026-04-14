'use client';

import { memo, useEffect, useRef, useState } from 'react';
import {
  ArrowLeft,
  Loader2,
  FileText,
  Cloud,
  Trash2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/ui/status-badge';
import { cn } from '@/lib/utils';

type SaveState = 'idle' | 'saving' | 'saved' | 'error';

type AssignmentTemplateStudioHeaderProps = {
  title: string;
  onTitleChange: (title: string) => void;
  titleError: string | null;
  titleHighlightSignal?: number;
  status: string;
  isDraft: boolean;
  isReadOnly: boolean;
  saveState: SaveState;
  isPublishing: boolean;
  isSaving: boolean;
  onPublish: () => void;
  onSave: () => void;
  onDeleteDraft: () => void;
  onCancel: () => void;
};

function AssignmentTemplateStudioHeader({
  title,
  onTitleChange,
  titleError,
  titleHighlightSignal,
  status,
  isDraft,
  isReadOnly,
  saveState,
  isPublishing,
  isSaving,
  onPublish,
  onSave,
  onDeleteDraft,
  onCancel,
}: AssignmentTemplateStudioHeaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isHighlighted, setIsHighlighted] = useState(false);

  useEffect(() => {
    if (!titleHighlightSignal) return;
    const input = inputRef.current;
    if (!input) return;
    input.scrollIntoView({ behavior: 'smooth', block: 'center' });
    input.focus();
    setIsHighlighted(true);
    const timeout = window.setTimeout(() => setIsHighlighted(false), 2200);
    return () => window.clearTimeout(timeout);
  }, [titleHighlightSignal]);

  return (
    <header className="min-h-16 border-b border-border bg-card flex items-center justify-between px-4 py-2 gap-4 shrink-0">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0"
          onClick={onCancel}
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="sr-only">Back to assignment templates</span>
        </Button>

        <div className="w-9 h-9 bg-primary rounded-md flex items-center justify-center text-primary-foreground shrink-0">
          <FileText className="h-5 w-5" />
        </div>

        <div
          className={cn(
            'flex flex-col min-w-0 flex-1 rounded-lg px-2 py-1.5 transition-shadow',
            isHighlighted && 'ring-2 ring-amber-400/70 ring-offset-2 ring-offset-card',
          )}
        >
          <div className="min-w-0">
            <input
              ref={inputRef}
              type="text"
              value={title}
              onChange={(e) => onTitleChange(e.target.value)}
              className={cn(
                'bg-transparent border-none p-0 text-sm font-semibold text-foreground focus:outline-none focus:ring-0 w-full truncate placeholder:text-muted-foreground',
                titleError && 'text-destructive',
              )}
              placeholder="Untitled Assignment Template"
            />
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <StatusBadge status={status || 'ACTIVE'} className="text-[10px]" />
            {/* Save state indicator */}
            <span className="text-[10px] text-muted-foreground flex items-center gap-1 font-medium">
              {isReadOnly && (
                <span className="text-amber-600 dark:text-amber-400">
                  Read-only (linked to assignments)
                </span>
              )}
              {!isReadOnly && saveState === 'saving' && (
                <>
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                  Saving...
                </>
              )}
              {!isReadOnly && saveState === 'saved' && (
                <>
                  <Cloud className="h-3 w-3 text-green-500" />
                  All changes saved
                </>
              )}
              {!isReadOnly && saveState === 'error' && (
                <span className="text-destructive">Save failed</span>
              )}
            </span>
            {titleError && (
              <span className="text-[10px] text-destructive font-medium">
                {titleError}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {isDraft && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onDeleteDraft}
            className="hidden sm:inline-flex text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="h-3.5 w-3.5 mr-1.5" />
            Delete Draft
          </Button>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onCancel}
          className="hidden sm:inline-flex"
        >
          {isDraft ? 'Close' : 'Cancel'}
        </Button>
        {isDraft ? (
          <Button
            type="button"
            size="sm"
            disabled={isPublishing}
            onClick={onPublish}
          >
            {isPublishing && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
            Publish
          </Button>
        ) : (
          <Button
            type="button"
            size="sm"
            disabled={isSaving || isReadOnly}
            onClick={onSave}
          >
            {isSaving && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
            Save Changes
          </Button>
        )}
      </div>
    </header>
  );
}

export default memo(AssignmentTemplateStudioHeader);
