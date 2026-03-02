'use client';

import { Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { QuestionData } from '@/lib/assessment-api';

type MoodMeterFieldsProps = {
  data: QuestionData;
  onChange: (data: QuestionData) => void;
};

export default function MoodMeterFields({ data, onChange }: MoodMeterFieldsProps) {
  const labels = data.labels ?? [];

  function updateLabel(index: number, value: string) {
    const next = [...labels];
    next[index] = value;
    onChange({ ...data, labels: next });
  }

  function addLabel() {
    onChange({ ...data, labels: [...labels, ''] });
  }

  function removeLabel(index: number) {
    onChange({ ...data, labels: labels.filter((_, i) => i !== index) });
  }

  return (
    <div className="space-y-3">
      <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Labels
      </Label>
      {labels.map((label, i) => (
        <div key={i} className="flex items-center gap-2">
          <Input
            placeholder={`Label ${i + 1}`}
            value={label}
            onChange={(e) => updateLabel(i, e.target.value)}
            className="flex-1"
          />
          <Button variant="ghost" size="icon" onClick={() => removeLabel(i)} className="h-8 w-8 text-destructive">
            <X className="h-4 w-4" />
          </Button>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={addLabel}>
        <Plus className="mr-1 h-3 w-3" /> Add Label
      </Button>
    </div>
  );
}
