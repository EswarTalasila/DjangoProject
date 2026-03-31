'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { listCourses, type CourseSummary } from '@/lib/course-api';
import { listMySubmissions, type SubmissionCompactDTO } from '@/lib/submission-api';

export default function StudentView() {
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [submissions, setSubmissions] = useState<SubmissionCompactDTO[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      try {
        const [courseList, submissionList] = await Promise.all([
          listCourses(),
          listMySubmissions(),
        ]);
        if (cancelled) return;
        setCourses(courseList);
        setSubmissions(submissionList);
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const inProgressCount = useMemo(
    () =>
      submissions.filter(
        (submission) => submission.status === 'NOT_STARTED' || submission.status === 'IN_PROGRESS',
      ).length,
    [submissions],
  );
  const submittedCount = useMemo(
    () => submissions.filter((submission) => submission.status === 'SUBMITTED').length,
    [submissions],
  );
  const gradedCount = useMemo(
    () => submissions.filter((submission) => submission.status === 'GRADED').length,
    [submissions],
  );

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Student Dashboard
        </h1>
        <p className="text-muted-foreground mt-1">
          Track your courses, active work, and graded submissions.
        </p>
      </div>

      <div className="flex items-center gap-0 divide-x divide-border bg-muted px-4 py-3 rounded-sm overflow-x-auto">
        {[
          { label: 'Courses', value: isLoading ? '—' : courses.length },
          { label: 'In Progress', value: isLoading ? '—' : inProgressCount },
          { label: 'Submitted', value: isLoading ? '—' : submittedCount },
          { label: 'Graded', value: isLoading ? '—' : gradedCount },
        ].map((stat) => (
          <div key={stat.label} className="flex items-baseline gap-2 px-6 first:pl-0 last:pr-0">
            <span className="text-2xl font-bold text-foreground">{stat.value}</span>
            <span className="text-sm text-muted-foreground whitespace-nowrap">{stat.label}</span>
          </div>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-sm border border-border bg-card p-6">
          <h2 className="text-lg font-semibold text-foreground">Courses</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {isLoading
              ? 'Loading your courses...'
              : courses.length === 0
                ? 'You are not enrolled in any courses yet.'
                : `You are enrolled in ${courses.length} course${courses.length !== 1 ? 's' : ''}.`}
          </p>
          <div className="mt-4">
            <Button asChild>
              <Link href="/dashboard/courses">
                Open My Courses
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>

        <div className="rounded-sm border border-border bg-card p-6">
          <h2 className="text-lg font-semibold text-foreground">Submissions</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {isLoading
              ? 'Loading your submissions...'
              : submissions.length === 0
                ? 'No submissions yet. Start an assignment from your course page.'
                : `${inProgressCount} in progress, ${submittedCount} submitted, ${gradedCount} graded.`}
          </p>
          <div className="mt-4">
            <Button asChild variant="outline">
              <Link href="/dashboard/submissions">
                Open My Submissions
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
