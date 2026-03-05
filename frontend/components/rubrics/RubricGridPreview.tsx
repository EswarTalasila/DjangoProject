'use client';

import type { CriterionInput, RubricCriterion } from '@/lib/rubric-api';

type CriterionLike = CriterionInput | RubricCriterion;

type RubricGridPreviewProps = {
  criteria: CriterionLike[];
  title?: string;
};

function getLevels(criterion: CriterionLike) {
  return criterion.levels ?? [];
}

function getLabel(level: { label?: string }, index: number): string {
  return level.label?.trim() || `Level ${index + 1}`;
}

export default function RubricGridPreview({
  criteria,
  title = 'Live Rubric Grid Preview',
}: RubricGridPreviewProps) {
  if (!criteria.length) {
    return (
      <div className="rounded-sm border border-border bg-card p-3">
        <p className="text-xs text-muted-foreground">Add criteria to see the rubric grid preview.</p>
      </div>
    );
  }

  const maxLevels = Math.max(...criteria.map((criterion) => getLevels(criterion).length), 0);
  const weightedMax = criteria.reduce((sum, criterion) => {
    const levels = getLevels(criterion);
    const maxPoints = levels.reduce(
      (best, level) => Math.max(best, level.points ?? 0),
      0,
    );
    const weight = criterion.weight ?? 1;
    return sum + maxPoints * weight;
  }, 0);

  return (
    <div className="rounded-sm border border-border bg-card">
      <div className="px-3 py-2 border-b border-border">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </h4>
        <p className="text-xs text-muted-foreground mt-1">
          Weighted max total: {weightedMax.toFixed(2)} points
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px]">
          <thead className="bg-muted border-b border-border">
            <tr>
              <th className="text-left px-3 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground w-[220px]">
                Criterion
              </th>
              <th className="text-left px-3 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground w-[90px]">
                Weight
              </th>
              {Array.from({ length: maxLevels }).map((_, levelIndex) => (
                <th
                  key={levelIndex}
                  className="text-left px-3 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground"
                >
                  Level {levelIndex + 1}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {criteria.map((criterion, criterionIndex) => {
              const levels = getLevels(criterion);
              return (
                <tr key={criterionIndex} className="even:bg-muted/30 border-b border-border align-top">
                  <td className="px-3 py-2 text-sm text-foreground">
                    <p className="font-medium">{criterion.title?.trim() || `Criterion ${criterionIndex + 1}`}</p>
                    {criterion.description && (
                      <p className="text-xs text-muted-foreground mt-1">{criterion.description}</p>
                    )}
                  </td>
                  <td className="px-3 py-2 text-sm text-foreground">{criterion.weight ?? 1}</td>
                  {Array.from({ length: maxLevels }).map((_, levelIndex) => {
                    const level = levels[levelIndex];
                    if (!level) {
                      return <td key={levelIndex} className="px-3 py-2 text-xs text-muted-foreground">-</td>;
                    }
                    return (
                      <td key={levelIndex} className="px-3 py-2 text-sm text-foreground">
                        <p className="font-medium">{getLabel(level, levelIndex)}</p>
                        <p className="text-xs text-muted-foreground">{level.points ?? 0} pts</p>
                        {level.description && (
                          <p className="text-xs text-muted-foreground mt-1">{level.description}</p>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
