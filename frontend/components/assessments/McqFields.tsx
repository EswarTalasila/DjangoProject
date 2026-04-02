'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, GripVertical, Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { QuestionData, McqChoice } from '@/lib/assessment-api';

type McqFieldsProps = {
  data: QuestionData;
  onChange: (data: QuestionData) => void;
};

export default function McqFields({ data, onChange }: McqFieldsProps) {
  const choices = data.choices ?? [];
  const [isChoicesOpen, setIsChoicesOpen] = useState(true);
  const [draggingChoiceIndex, setDraggingChoiceIndex] = useState<number | null>(
    null,
  );
  const [dragOverChoiceIndex, setDragOverChoiceIndex] = useState<number | null>(
    null,
  );

  function updateChoice(index: number, updated: McqChoice) {
    const next = [...choices];
    next[index] = updated;
    onChange({ ...data, choices: next });
  }

  function addChoice() {
    onChange({ ...data, choices: [...choices, { prompt: '', score: 0 }] });
  }

  function removeChoice(index: number) {
    onChange({ ...data, choices: choices.filter((_, i) => i !== index) });
  }

  function moveChoice(from: number, to: number) {
    if (from === to || from < 0 || to < 0 || from >= choices.length || to >= choices.length) {
      return;
    }
    const next = [...choices];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    onChange({ ...data, choices: next });
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Choices
        </Label>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="text-sm text-muted-foreground"
          onClick={() => setIsChoicesOpen((v) => !v)}
        >
          {isChoicesOpen ? (
            <ChevronUp className="mr-1.5 h-4 w-4" />
          ) : (
            <ChevronDown className="mr-1.5 h-4 w-4" />
          )}
          {isChoicesOpen ? 'Hide' : 'Show'} ({choices.length})
        </Button>
      </div>

      {!isChoicesOpen && (
        <p className="text-sm text-muted-foreground">
          Choices hidden. Expand to edit order, text, and points.
        </p>
      )}

      {isChoicesOpen && (
        <>
          <p className="text-sm text-muted-foreground">
            Drag by the handle to reorder. Points are awarded when that choice is selected.
          </p>

          <div className="rounded-lg border border-border overflow-hidden">
            <div className="grid grid-cols-[minmax(0,1fr)_170px_48px] bg-muted border-b border-border text-xs uppercase tracking-wider font-semibold text-muted-foreground">
              <div className="px-3 py-2.5">Choice Text</div>
              <div className="px-3 py-2.5">Points</div>
              <div className="px-3 py-2.5 text-right"> </div>
            </div>

            {choices.length === 0 && (
              <div className="px-3 py-4 text-xs text-muted-foreground">
                No choices yet.
              </div>
            )}

            <div className="divide-y divide-border">
              {choices.map((choice, i) => (
                <div
                  key={i}
                  data-choice-row="true"
                  className={`relative grid grid-cols-[minmax(0,1fr)_170px_48px] items-center gap-2 py-2 pr-1 ${
                    dragOverChoiceIndex === i && draggingChoiceIndex !== i
                      ? 'bg-accent/40 outline outline-1 outline-primary'
                      : 'bg-card'
                  }`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    if (draggingChoiceIndex !== null && draggingChoiceIndex !== i) {
                      setDragOverChoiceIndex(i);
                    }
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (draggingChoiceIndex !== null) {
                      moveChoice(draggingChoiceIndex, i);
                    }
                    setDraggingChoiceIndex(null);
                    setDragOverChoiceIndex(null);
                  }}
                  onDragEnd={() => {
                    setDraggingChoiceIndex(null);
                    setDragOverChoiceIndex(null);
                  }}
                >
                  <span
                    role="button"
                    tabIndex={0}
                    draggable
                    aria-label={`Drag choice ${i + 1}`}
                    className="absolute inset-y-0 left-0 inline-flex w-8 cursor-grab items-center justify-center border-r border-border bg-muted/30 text-muted-foreground hover:text-foreground active:cursor-grabbing"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                      }
                    }}
                    onDragStart={(e) => {
                      e.stopPropagation();
                      const row = e.currentTarget.closest(
                        '[data-choice-row="true"]',
                      ) as HTMLElement | null;
                      if (row) {
                        e.dataTransfer.setDragImage(row, 24, 18);
                      }
                      setDraggingChoiceIndex(i);
                      setDragOverChoiceIndex(i);
                      e.dataTransfer.effectAllowed = 'move';
                      e.dataTransfer.setData('text/plain', String(i));
                    }}
                    onDragEnd={(e) => {
                      e.stopPropagation();
                      setDraggingChoiceIndex(null);
                      setDragOverChoiceIndex(null);
                    }}
                  >
                    <GripVertical className="h-3.5 w-3.5" />
                  </span>

                  <div className="flex items-center gap-2 pl-10 pr-1">
                    <span className="w-7 shrink-0 text-right text-sm font-medium text-muted-foreground">
                      {i + 1}.
                    </span>
                    <Input
                      placeholder="Choice text"
                      value={choice.prompt}
                      onChange={(e) => updateChoice(i, { ...choice, prompt: e.target.value })}
                      className="h-10 text-sm"
                    />
                  </div>

                  <div className="flex items-center gap-1.5">
                    <div className="flex flex-col gap-0.5">
                      <button
                        type="button"
                        onClick={() => updateChoice(i, { ...choice, score: choice.score + 1 })}
                        className="h-5 w-7 flex items-center justify-center rounded border border-border bg-muted hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <ChevronUp className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => updateChoice(i, { ...choice, score: Math.max(0, choice.score - 1) })}
                        className="h-5 w-7 flex items-center justify-center rounded border border-border bg-muted hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <ChevronDown className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <Input
                      type="number"
                      placeholder="0"
                      value={choice.score}
                      onChange={(e) =>
                        updateChoice(i, { ...choice, score: Number(e.target.value) || 0 })
                      }
                      className="h-10 text-sm text-center font-mono font-bold [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    />
                    <span className="text-xs text-muted-foreground font-medium shrink-0">pts</span>
                  </div>

                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeChoice(i)}
                    className="h-10 w-10 text-destructive justify-self-end"
                  >
                    <X className="h-5 w-5" />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          <Button type="button" variant="outline" onClick={addChoice} className="gap-2">
            <Plus className="h-4 w-4" /> Add Choice
          </Button>
        </>
      )}
      <div className="flex items-center gap-2">
        <Checkbox
          id="selectAll"
          checked={data.selectAll ?? false}
          onCheckedChange={(checked) => onChange({ ...data, selectAll: checked === true })}
        />
        <Label htmlFor="selectAll" className="text-sm">Select all that apply</Label>
      </div>
    </div>
  );
}
