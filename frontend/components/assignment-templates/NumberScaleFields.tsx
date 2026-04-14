'use client';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { QuestionData } from '@/lib/assignment-template-api';

type NumberScaleFieldsProps = {
  data: QuestionData;
  onChange: (data: QuestionData) => void;
};

export default function NumberScaleFields({ data, onChange }: NumberScaleFieldsProps) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label>Min</Label>
          <Input
            type="number"
            value={data.min ?? 1}
            onChange={(e) => onChange({ ...data, min: Number(e.target.value) || 0 })}
          />
        </div>
        <div className="space-y-2">
          <Label>Max</Label>
          <Input
            type="number"
            value={data.max ?? 5}
            onChange={(e) => onChange({ ...data, max: Number(e.target.value) || 0 })}
          />
        </div>
        <div className="space-y-2">
          <Label>Target (optional)</Label>
          <Input
            type="number"
            value={data.target ?? ''}
            onChange={(e) => {
              const val = e.target.value;
              onChange({ ...data, target: val === '' ? null : Number(val) });
            }}
          />
        </div>
      </div>
      {data.min !== undefined && data.max !== undefined && data.min >= data.max && (
        <p className="text-sm text-destructive">Min must be less than Max</p>
      )}
    </div>
  );
}
