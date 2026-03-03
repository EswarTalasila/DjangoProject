'use client';

import type { Quadrant } from '@/lib/visualization-api';

const QUADRANT_STYLES: Record<string, string> = {
  'High Energy / Positive': 'bg-brand-gold/30 border-brand-gold',
  'High Energy / Negative': 'bg-status-error-bg border-status-error',
  'Low Energy / Positive': 'bg-brand-sage/30 border-brand-sage',
  'Low Energy / Negative': 'bg-brand-sky/30 border-brand-sky',
};

const GRID_ORDER = [
  'High Energy / Negative',
  'High Energy / Positive',
  'Low Energy / Negative',
  'Low Energy / Positive',
];

export default function MoodMeterGrid({
  quadrants,
  totalResponses,
}: {
  quadrants: Quadrant[];
  totalResponses: number;
}) {
  const byLabel = Object.fromEntries(quadrants.map((q) => [q.label, q]));

  return (
    <div className="grid grid-cols-2 gap-3">
      {GRID_ORDER.map((label) => {
        const q = byLabel[label] ?? { label, count: 0, pct: 0 };
        const style = QUADRANT_STYLES[label] ?? 'bg-muted border-border';
        return (
          <div
            key={label}
            className={`flex flex-col items-center justify-center rounded-xl border-2 p-6 ${style}`}
          >
            <p className="text-3xl font-bold">{Math.round(q.pct * 100)}%</p>
            <p className="text-sm font-medium mt-1">{label}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{q.count} responses</p>
          </div>
        );
      })}
      <p className="col-span-2 text-center text-xs text-muted-foreground mt-1">
        {totalResponses} total responses
      </p>
    </div>
  );
}
