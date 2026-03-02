'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { listCourses, type CourseSummary } from '@/lib/course-api';

export default function TeacherView() {
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    void listCourses()
      .then(setCourses)
      .finally(() => setIsLoading(false));
  }, []);

  const totalStudents = courses.reduce((sum, c) => sum + c.studentCount, 0);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Teacher Dashboard</h1>
        <p className="text-muted-foreground mt-1">Overview of your courses and students.</p>
      </div>

      <div className="flex items-center gap-0 divide-x divide-border bg-muted px-4 py-3 rounded-sm">
        {[
          { label: 'Students', value: isLoading ? '\u2014' : totalStudents },
          { label: 'Active Courses', value: isLoading ? '\u2014' : courses.length },
          { label: 'Pending Grades', value: '\u2014' },
        ].map((stat) => (
          <div key={stat.label} className="flex items-baseline gap-2 px-6 first:pl-0 last:pr-0">
            <span className="text-2xl font-bold text-foreground">{stat.value}</span>
            <span className="text-sm text-muted-foreground">{stat.label}</span>
          </div>
        ))}
      </div>

      <div className="rounded-sm border border-border bg-card p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Courses</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {isLoading
                ? 'Loading...'
                : courses.length === 0
                  ? 'No courses yet. Create your first course to get started.'
                  : `${courses.length} course${courses.length !== 1 ? 's' : ''} with ${totalStudents} total student${totalStudents !== 1 ? 's' : ''}.`}
            </p>
          </div>
          <Button asChild>
            <Link href="/dashboard/courses">
              Manage Courses
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
