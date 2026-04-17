'use client';

import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { LevelInput } from '@/lib/rubric-api';

type LevelRowProps = {
  index: number;
  level: LevelInput;
  onChange: (updated: LevelInput) => void;
  onRemove: () => void;
};

export default function LevelRow({ index, level, onChange, onRemove }: LevelRowProps) {
  return (
    <div className="flex items-end gap-3 rounded-sm border border-border bg-card p-3">
      <div className="space-y-1 flex-1 min-w-0">
        <Label className="text-xs text-muted-foreground">Label</Label>
        <Input
          placeholder={`Level ${index + 1} label`}
          value={level.label}
          onChange={(e) => onChange({ ...level, label: e.target.value })}
        />
      </div>

      <div className="space-y-1 w-24">
        <div className="flex items-center gap-1">
          <Label className="text-xs text-muted-foreground">Points</Label>
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="text-[10px] text-muted-foreground hover:text-foreground">
                i
              </button>
            </TooltipTrigger>
            <TooltipContent sideOffset={6} className="max-w-xs">
              Raw score for this level before criterion weight is applied.
            </TooltipContent>
          </Tooltip>
        </div>
        <Input
          type="number"
          min={0}
          step="0.5"
          value={level.points}
          onChange={(e) => onChange({ ...level, points: Number(e.target.value) || 0 })}
        />
      </div>

      <div className="space-y-1 flex-1 min-w-0">
        <Label className="text-xs text-muted-foreground">Description</Label>
        <Input
          placeholder="Optional description"
          value={level.description ?? ''}
          onChange={(e) => onChange({ ...level, description: e.target.value })}
        />
      </div>

      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-destructive hover:text-destructive shrink-0"
        onClick={onRemove}
      >
        <Trash2 className="h-4 w-4" />
        <span className="sr-only">Remove level</span>
      </Button>
    </div>
  );
}
