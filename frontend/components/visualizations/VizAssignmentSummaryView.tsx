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
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
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
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {data?.assignmentTitle ?? `Assignment ${assignmentId}`}
          </h1>
          <p className="text-muted-foreground mt-1">
            {data
              ? data.assignmentTemplateTitle
                ? `${data.assignmentTemplateTitle}${data.assignmentTemplateCategory ? ` · ${data.assignmentTemplateCategory}` : ''}`
                : (data.assignmentTemplateCategory ?? 'Assignment summary')
              : 'Loading...'}
          </p>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {loading && <p className="text-sm text-muted-foreground">Loading...</p>}

      {!loading && data && (
        <>
          {/* Stats row */}
          <Card>
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

          {/* Score summary */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground">Average</p>
                <p className="text-2xl font-bold">{fmt(data.avgScore)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground">Median</p>
                <p className="text-2xl font-bold">{fmt(data.medianScore)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground">High</p>
                <p className="text-2xl font-bold">{fmt(data.highScore)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground">Low</p>
                <p className="text-2xl font-bold">{fmt(data.lowScore)}</p>
              </CardContent>
            </Card>
          </div>

          {/* Distribution chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Grade Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              {data.gradedCount === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  No graded submissions yet.
                </p>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data.distribution} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
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
