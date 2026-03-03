'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { type CourseSummaryDTO, fetchCourseSummary } from '@/lib/visualization-api';

export default function VizCourseSummaryView({
  courseId,
  role,
}: {
  courseId: number;
  role: string;
}) {
  const [data, setData] = useState<CourseSummaryDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const d = await fetchCourseSummary(courseId);
      setData(d);
    } catch {
      setError('Failed to load course summary.');
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    load();
  }, [load]);

  const fmt = (v: number | null) => (v != null ? v.toFixed(1) : 'N/A');
  const pct = (v: number | null) =>
    v != null ? `${Math.round(v * 100)}%` : 'N/A';

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center gap-3">
        <Link
          href="/dashboard/visualizations"
          className="rounded-md p-1.5 hover:bg-muted transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {data?.courseName ?? `Course ${courseId}`}
          </h1>
          <p className="text-muted-foreground mt-1">
            {data ? `${data.enrolledCount} enrolled students` : 'Loading...'}
          </p>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {loading && <p className="text-sm text-muted-foreground">Loading...</p>}

      {!loading && data && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Assignments</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {data.assignments.length === 0 ? (
                <p className="p-6 text-sm text-muted-foreground">No assignments found.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted border-b border-border">
                      {data.assignments[0]?.assessmentTitle !== undefined && (
                        <TableHead className="text-xs font-semibold uppercase tracking-wider">
                          Title
                        </TableHead>
                      )}
                      <TableHead className="text-xs font-semibold uppercase tracking-wider">
                        Category
                      </TableHead>
                      <TableHead className="text-xs font-semibold uppercase tracking-wider text-right">
                        Submitted
                      </TableHead>
                      <TableHead className="text-xs font-semibold uppercase tracking-wider text-right">
                        Completion
                      </TableHead>
                      <TableHead className="text-xs font-semibold uppercase tracking-wider text-right">
                        Avg Score
                      </TableHead>
                      <TableHead className="text-xs font-semibold uppercase tracking-wider text-right">
                        Pending
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.assignments.map((a, i) => {
                      const row = (
                        <TableRow
                          key={a.assignmentId ?? i}
                          className="even:bg-muted/50 hover:bg-accent transition-colors cursor-pointer"
                        >
                          {a.assessmentTitle !== undefined && (
                            <TableCell className="font-medium text-sm">
                              {a.assessmentTitle}
                            </TableCell>
                          )}
                          <TableCell className="text-sm">
                            {a.assessmentCategory ?? '-'}
                          </TableCell>
                          <TableCell className="text-sm text-right">
                            {a.submittedCount}/{a.totalStudents}
                          </TableCell>
                          <TableCell className="text-sm text-right">
                            {pct(a.completionPct)}
                          </TableCell>
                          <TableCell className="text-sm text-right">
                            {fmt(a.avgScore)}
                          </TableCell>
                          <TableCell className="text-sm text-right">
                            {a.pendingGrades > 0 ? (
                              <span className="rounded-full bg-status-warning-bg px-2 py-0.5 text-xs font-medium text-status-warning">
                                {a.pendingGrades}
                              </span>
                            ) : (
                              '0'
                            )}
                          </TableCell>
                        </TableRow>
                      );

                      return a.assignmentId != null ? (
                        <Link
                          key={a.assignmentId}
                          href={`/dashboard/visualizations/assignments/${a.assignmentId}`}
                          legacyBehavior
                        >
                          {row}
                        </Link>
                      ) : (
                        row
                      );
                    })}
                  </TableBody>
                </Table>
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
