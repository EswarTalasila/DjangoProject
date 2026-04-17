'use client';

import { ChevronDown, ChevronUp, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { CriterionInput, LevelInput } from '@/lib/rubric-api';
import LevelRow from './LevelRow';

type CriterionBlockProps = {
  index: number;
  criterion: CriterionInput;
  onChange: (updated: CriterionInput) => void;
  onRemove: () => void;
  onMoveUp: (() => void) | null;
  onMoveDown: (() => void) | null;
};

function emptyLevel(): LevelInput {
  return { label: '', points: 0, description: '' };
}

export default function CriterionBlock({
  index,
  criterion,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
}: CriterionBlockProps) {
  const levels = criterion.levels ?? [];

  function handleLevelChange(levelIndex: number, updated: LevelInput) {
    const newLevels = levels.map((l, i) => (i === levelIndex ? updated : l));
    onChange({ ...criterion, levels: newLevels });
  }

  function handleLevelRemove(levelIndex: number) {
    onChange({ ...criterion, levels: levels.filter((_, i) => i !== levelIndex) });
  }

  function addLevel() {
    onChange({ ...criterion, levels: [...levels, emptyLevel()] });
  }

  return (
    <div className="rounded-sm border border-border bg-card p-4 space-y-4">
      {/* Criterion header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Criterion {index + 1}</h3>
        <div className="flex items-center gap-1">
          {onMoveUp && (
            <Button type="button" variant="ghost" size="icon" onClick={onMoveUp} className="h-8 w-8">
              <ChevronUp className="h-4 w-4" />
            </Button>
          )}
          {onMoveDown && (
            <Button type="button" variant="ghost" size="icon" onClick={onMoveDown} className="h-8 w-8">
              <ChevronDown className="h-4 w-4" />
            </Button>
          )}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onRemove}
            className="h-8 w-8 text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Criterion fields */}
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 space-y-2">
          <Label>Title</Label>
          <Input
            placeholder="Criterion title..."
            value={criterion.title}
            onChange={(e) => onChange({ ...criterion, title: e.target.value })}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-1.5">
            <Label>Weight (%)</Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <button type="button" className="text-xs text-muted-foreground hover:text-foreground">
                  i
                </button>
              </TooltipTrigger>
              <TooltipContent sideOffset={6} className="max-w-xs">
                How much this criterion counts toward the total rubric score.
                Example: a criterion weighted 40% means it accounts for 40% of the final grade.
                Weights across all criteria should add up to 100%.
              </TooltipContent>
            </Tooltip>
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={1}
              max={100}
              step={1}
              value={Math.round((criterion.weight ?? 1) * 100)}
              onChange={(e) => {
                const pct = Math.max(1, Math.min(100, Math.round(Number(e.target.value) || 1)));
                onChange({ ...criterion, weight: pct / 100 });
              }}
              className="w-20"
            />
            <span className="text-sm text-muted-foreground">%</span>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <Label>Description</Label>
        <Input
          placeholder="Optional criterion description..."
          value={criterion.description ?? ''}
          onChange={(e) => onChange({ ...criterion, description: e.target.value })}
        />
      </div>

      {/* Levels */}
      <div className="space-y-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Levels ({levels.length})
        </h4>

        {levels.map((level, i) => (
          <LevelRow
            key={i}
            index={i}
            level={level}
            onChange={(updated) => handleLevelChange(i, updated)}
            onRemove={() => handleLevelRemove(i)}
          />
        ))}

        <Button type="button" variant="outline" size="sm" onClick={addLevel}>
          <Plus className="mr-2 h-3 w-3" />
          Add Level
        </Button>
      </div>
    </div>
  );
}
