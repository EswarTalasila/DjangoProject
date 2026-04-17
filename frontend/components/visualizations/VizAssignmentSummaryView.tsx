'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { type AssignmentSummaryDTO, fetchAssignmentSummary } from '@/lib/visualization-api';

const BAR_COLORS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
];

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-h-24 flex-col items-center justify-center px-4 py-5 text-center">
      <p className="text-2xl font-semibold tracking-tight">{value}</p>
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
    </div>
  );
}

export default function VizAssignmentSummaryView({
  assignmentId,
  role,
}: {
  assignmentId: number;
  role: string;
}) {
  const [data, setData] = useState<AssignmentSummaryDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const summaryData = await fetchAssignmentSummary(assignmentId);
      setData(summaryData);
    } catch {
      setError('Failed to load assignment summary.');
    } finally {
      setLoading(false);
    }
  }, [assignmentId]);

  useEffect(() => {
    load();
  }, [load]);

  const fmt = (v: number | null) => (v != null ? v.toFixed(1) : 'N/A');
  const pct = (v: number | null) =>
    v != null ? `${Math.round(v * 100)}%` : 'N/A';

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="flex items-center gap-3">
        <Link
          href="/dashboard/visualizations"
          className="rounded-md p-1.5 hover:bg-muted transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Assignment summary
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">
            {data?.assignmentTitle ?? `Assignment ${assignmentId}`}
          </h1>
          <p className="text-sm text-muted-foreground">
            {data
              ? data.assignmentTemplateTitle
                ? `${data.assignmentTemplateTitle}${data.assignmentTemplateCategory ? ` · ${data.assignmentTemplateCategory}` : ''}`
                : (data.assignmentTemplateCategory ?? 'Assignment summary')
              : 'Loading...'}
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-destructive/25 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}
      {loading && (
        <Card className="border-border/70 shadow-sm">
          <CardContent className="px-5 py-8 text-sm text-muted-foreground">Loading...</CardContent>
        </Card>
      )}

      {!loading && data && (
        <>
          <Card className="overflow-hidden border-border/70 shadow-sm">
            <CardContent className="p-0">
              <div className="grid grid-cols-2 overflow-hidden rounded-xl bg-border sm:grid-cols-4">
                <div className="bg-card">
                  <StatItem label="Total Students" value={String(data.totalStudents)} />
                </div>
                <div className="bg-card sm:border-l sm:border-border">
                  <StatItem label="Submitted" value={String(data.submittedCount)} />
                </div>
                <div className="bg-card border-t border-border sm:border-l sm:border-t-0 sm:border-border">
                  <StatItem label="Graded" value={String(data.gradedCount)} />
                </div>
                <div className="bg-card border-l border-t border-border sm:border-t-0">
                  <StatItem label="Completion" value={pct(data.completionPct)} />
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="border-border/70 shadow-sm">
              <CardContent className="p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Average
                </p>
                <p className="mt-2 text-xl font-semibold tracking-tight">{fmt(data.avgScore)}</p>
              </CardContent>
            </Card>
            <Card className="border-border/70 shadow-sm">
              <CardContent className="p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Median
                </p>
                <p className="mt-2 text-xl font-semibold tracking-tight">
                  {fmt(data.medianScore)}
                </p>
              </CardContent>
            </Card>
            <Card className="border-border/70 shadow-sm">
              <CardContent className="p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  High
                </p>
                <p className="mt-2 text-xl font-semibold tracking-tight">{fmt(data.highScore)}</p>
              </CardContent>
            </Card>
            <Card className="border-border/70 shadow-sm">
              <CardContent className="p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Low
                </p>
                <p className="mt-2 text-xl font-semibold tracking-tight">{fmt(data.lowScore)}</p>
              </CardContent>
            </Card>
          </div>

          <Card className="border-border/70 shadow-sm">
            <CardHeader className="border-b border-border/70 bg-muted/30">
              <div className="space-y-1">
                <CardTitle className="text-base">Grade Distribution</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Distribution updates as submissions are graded.
                </p>
              </div>
            </CardHeader>
            <CardContent>
              {data.gradedCount === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  No graded submissions yet.
                </p>
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={data.distribution} margin={{ top: 12, right: 20, bottom: 8, left: 12 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="range" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        borderRadius: '0.5rem',
                        border: '1px solid hsl(var(--border))',
                        background: 'hsl(var(--card))',
                      }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {data.distribution.map((_, idx) => (
                        <Cell key={idx} fill={BAR_COLORS[idx % BAR_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          <p className="text-xs text-muted-foreground">
            Generated at {new Date(data.generatedAt).toLocaleString()}
          </p>
        </>
      )}
    </div>
  );
}
