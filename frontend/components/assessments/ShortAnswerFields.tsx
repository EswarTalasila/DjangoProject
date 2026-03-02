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
      <div className="flex items-center gap-2">
        <Checkbox
          id="caseSensitive"
          checked={data.caseSensitive ?? false}
          onCheckedChange={(checked) => onChange({ ...data, caseSensitive: checked === true })}
        />
        <Label htmlFor="caseSensitive" className="text-sm">Case Sensitive</Label>
      </div>
      <div className="flex items-center gap-2">
        <Checkbox
          id="trim"
          checked={data.trim ?? true}
          onCheckedChange={(checked) => onChange({ ...data, trim: checked === true })}
        />
        <Label htmlFor="trim" className="text-sm">Trim Whitespace</Label>
      </div>
    </div>
  );
}
