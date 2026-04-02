'use client';

import type { QuestionData, QuestionKind } from '@/lib/assessment-api';
import MoodMeterInput from '@/components/questions/MoodMeterInput';
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
      <div className="space-y-4">
        <div className="rounded-md border border-border bg-muted/20 p-4 space-y-1">
          <p className="text-sm font-medium text-foreground">Mood Meter</p>
          <p className="text-sm text-muted-foreground">
            Students will see the Yale RULER Mood Meter — a 4-quadrant grid of 20
            emotions organized by energy level and pleasantness. No additional
            configuration needed.
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
            Student Preview
          </p>
          <MoodMeterInput value={null} onChange={() => {}} disabled />
        </div>
      </div>
    );
  }

  if (type === 'FILE_UPLOAD') {
    return (
      <div className="rounded-md border border-border bg-muted/20 p-4 space-y-1">
        <p className="text-sm font-medium text-foreground">File Upload</p>
        <p className="text-sm text-muted-foreground">
          Students can upload a PDF or image file as their response. Uploaded files
          will be stored and viewable by teachers during grading. Supports PDF, JPG, PNG, and WebP.
        </p>
      </div>
    );
  }

  return null;
}
