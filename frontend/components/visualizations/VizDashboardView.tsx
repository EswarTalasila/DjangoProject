'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { BarChart3, Users, BookOpen, Clock } from 'lucide-react';
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
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="rounded-lg bg-muted p-2.5">
          <Icon className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-bold">{value}</p>
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
    <div className="flex items-center justify-between rounded-lg border border-border bg-card p-4 hover:bg-accent transition-colors">
      <div className="space-y-1">
        <p className="font-medium">{course.courseName ?? 'Course'}</p>
        <p className="text-sm text-muted-foreground">
          {course.enrolledCount} students &middot; {course.assignmentCount} assignments
        </p>
      </div>
      <div className="flex items-center gap-6 text-sm">
        <div className="text-center">
          <p className="font-semibold">{completion}</p>
          <p className="text-muted-foreground">Completion</p>
        </div>
        <div className="text-center">
          <p className="font-semibold">{avg}</p>
          <p className="text-muted-foreground">Avg Score</p>
        </div>
        {course.pendingGrades > 0 && (
          <span className="rounded-full bg-status-warning-bg px-2.5 py-0.5 text-xs font-medium text-status-warning">
            {course.pendingGrades} pending
          </span>
        )}
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
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          {role === 'TEACHER'
            ? 'Overview of your courses and student performance.'
            : 'System-wide course and performance overview.'}
        </p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading && <p className="text-sm text-muted-foreground">Loading dashboard...</p>}

      {!loading && data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Courses" value={data.courses.length} icon={BookOpen} />
            <StatCard label="Students" value={totalStudents} icon={Users} />
            <StatCard label="Assignments" value={totalAssignments} icon={BarChart3} />
            <StatCard label="Pending Grades" value={totalPending} icon={Clock} />
          </div>

          <div>
            <h2 className="text-lg font-semibold mb-3">Courses</h2>
            {data.courses.length === 0 ? (
              <div className="rounded-lg border border-border bg-card p-8 text-center">
                <p className="text-sm text-muted-foreground">No courses found.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {data.courses.map((c, i) => (
                  <CourseRow key={c.courseId ?? i} course={c} />
                ))}
              </div>
            )}
          </div>

          <p className="text-xs text-muted-foreground">
            Generated at {new Date(data.generatedAt).toLocaleString()}
          </p>
        </>
      )}
    </div>
  );
}
