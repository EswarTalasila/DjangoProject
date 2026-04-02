'use client';

import type { QuestionData, QuestionKind } from '@/lib/assessment-api';
import McqFields from '../McqFields';
import ShortAnswerFields from '../ShortAnswerFields';
import NumberScaleFields from '../NumberScaleFields';

type QuestionTypeConfigProps = {
  type: QuestionKind;
  data: QuestionData;
  onChange: (data: QuestionData) => void;
};

export default function QuestionTypeConfig({
  type,
  data,
  onChange,
}: QuestionTypeConfigProps) {
  if (type === 'MULTIPLE_CHOICE') {
    return <McqFields data={data} onChange={onChange} />;
  }

  if (type === 'SHORT_ANSWER') {
    return <ShortAnswerFields data={data} onChange={onChange} />;
  }

  if (type === 'NUMBER_SCALE') {
    return <NumberScaleFields data={data} onChange={onChange} />;
  }

  if (type === 'MOOD_METER') {
    return (
      <div className="rounded-md border border-border bg-muted/20 p-4 space-y-2">
        <p className="text-sm font-medium text-foreground">Mood Meter</p>
        <p className="text-sm text-muted-foreground">
          Students will see the Yale RULER Mood Meter — a 4-quadrant grid of 20
          emotions organized by energy level and pleasantness. No additional
          configuration needed.
        </p>
      </div>
    );
  }

  return null;
}
