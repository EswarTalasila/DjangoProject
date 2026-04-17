'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, BarChart3, BookOpen, Clock, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { type DashboardCourse, type DashboardDTO, fetchDashboard } from '@/lib/visualization-api';

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
}) {
  return (
    <Card className="border-border/70 shadow-sm">
      <CardContent className="flex items-center gap-4 p-5">
        <div className="rounded-xl border border-border/70 bg-muted/60 p-2.5">
          <Icon className="h-5 w-5 text-foreground/70" />
        </div>
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            {label}
          </p>
          <p className="text-2xl font-semibold tracking-tight">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function CourseRow({ course }: { course: DashboardCourse }) {
  const completion =
    course.avgCompletionRate != null
      ? `${Math.round(course.avgCompletionRate * 100)}%`
      : 'N/A';
  const avg = course.avgScore != null ? course.avgScore.toFixed(1) : 'N/A';

  const inner = (
    <div className="flex flex-col gap-4 rounded-2xl border border-border/70 bg-card px-4 py-4 transition-colors hover:bg-accent/35 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 space-y-1">
        <p className="truncate text-base font-semibold tracking-tight">
          {course.courseName ?? 'Course'}
        </p>
        <p className="text-sm text-muted-foreground">
          {course.enrolledCount} students &middot; {course.assignmentCount} assignments
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:flex sm:items-center sm:justify-end sm:gap-6">
        <div className="min-w-[4.5rem] text-center">
          <p className="text-base font-semibold tracking-tight">{completion}</p>
          <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
            Completion
          </p>
        </div>
        <div className="min-w-[4.5rem] text-center">
          <p className="text-base font-semibold tracking-tight">{avg}</p>
          <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
            Avg Score
          </p>
        </div>
        {course.pendingGrades > 0 && (
          <span className="col-span-2 justify-self-start rounded-full bg-status-warning-bg px-2.5 py-0.5 text-xs font-medium text-status-warning sm:col-span-1 sm:justify-self-auto">
            {course.pendingGrades} pending
          </span>
        )}
        <ArrowRight className="hidden h-4 w-4 text-muted-foreground sm:block" />
      </div>
    </div>
  );

  return course.courseId != null ? (
    <Link href={`/dashboard/visualizations/courses/${course.courseId}`}>{inner}</Link>
  ) : (
    inner
  );
}

export default function VizDashboardView({ role }: { role: string }) {
  const [data, setData] = useState<DashboardDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const dashboardData = await fetchDashboard();
      setData(dashboardData);
    } catch {
      setError('Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const totalStudents = data?.courses.reduce((s, c) => s + c.enrolledCount, 0) ?? 0;
  const totalAssignments = data?.courses.reduce((s, c) => s + c.assignmentCount, 0) ?? 0;
  const totalPending = data?.courses.reduce((s, c) => s + c.pendingGrades, 0) ?? 0;

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="space-y-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
          Visualizations
        </p>
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Analytics Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
          {role === 'TEACHER'
            ? 'Overview of your courses and student performance.'
            : 'System-wide course and performance overview.'}
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
          <CardContent className="px-5 py-8 text-sm text-muted-foreground">
            Loading dashboard...
          </CardContent>
        </Card>
      )}

      {!loading && data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Courses" value={data.courses.length} icon={BookOpen} />
            <StatCard label="Students" value={totalStudents} icon={Users} />
            <StatCard label="Assignments" value={totalAssignments} icon={BarChart3} />
            <StatCard label="Pending Grades" value={totalPending} icon={Clock} />
          </div>

          <section className="space-y-4">
            <div className="flex items-end justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold tracking-tight">Courses</h2>
                <p className="text-sm text-muted-foreground">
                  Open a course summary to review completion and score trends.
                </p>
              </div>
              <p className="hidden text-xs text-muted-foreground sm:block">
                {data.courses.length} total
              </p>
            </div>
            {data.courses.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border bg-card/70 p-10 text-center">
                <p className="text-sm text-muted-foreground">No courses found.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {data.courses.map((c, i) => (
                  <CourseRow key={c.courseId ?? i} course={c} />
                ))}
              </div>
            )}
          </section>

          <p className="text-xs text-muted-foreground">
            Generated at {new Date(data.generatedAt).toLocaleString()}
          </p>
        </>
      )}
    </div>
  );
}
