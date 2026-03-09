'use client';

import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import type { QuestionData } from '@/lib/assessment-api';

type ShortAnswerFieldsProps = {
  data: QuestionData;
  onChange: (data: QuestionData) => void;
};

export default function ShortAnswerFields({ data, onChange }: ShortAnswerFieldsProps) {
  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Checkbox
            id="caseSensitive"
            checked={data.caseSensitive ?? false}
            onCheckedChange={(checked) => onChange({ ...data, caseSensitive: checked === true })}
          />
          <Label htmlFor="caseSensitive" className="text-sm">Case Sensitive</Label>
        </div>
        <p className="text-xs text-muted-foreground ml-6">
          When enabled, uppercase/lowercase must match exactly (example: DNA is different from dna).
        </p>
      </div>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Checkbox
            id="trim"
            checked={data.trim ?? true}
            onCheckedChange={(checked) => onChange({ ...data, trim: checked === true })}
          />
          <Label htmlFor="trim" className="text-sm">Trim Whitespace</Label>
        </div>
        <p className="text-xs text-muted-foreground ml-6">
          Ignores extra spaces at the start/end and treats repeated spaces as equivalent when comparing answers.
        </p>
      </div>
    </div>
  );
}
