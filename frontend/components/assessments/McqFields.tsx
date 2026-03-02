'use client';

import { Plus, X } from 'lucide-react';
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

  return (
    <div className="space-y-3">
      <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Choices
      </Label>
      {choices.map((choice, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground w-6 text-right">{i + 1}.</span>
          <Input
            placeholder="Choice text"
            value={choice.prompt}
            onChange={(e) => updateChoice(i, { ...choice, prompt: e.target.value })}
            className="flex-1"
          />
          <Input
            type="number"
            placeholder="Score"
            value={choice.score}
            onChange={(e) => updateChoice(i, { ...choice, score: Number(e.target.value) || 0 })}
            className="w-20"
          />
          <Button variant="ghost" size="icon" onClick={() => removeChoice(i)} className="h-8 w-8 text-destructive">
            <X className="h-4 w-4" />
          </Button>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={addChoice}>
        <Plus className="mr-1 h-3 w-3" /> Add Choice
      </Button>
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
