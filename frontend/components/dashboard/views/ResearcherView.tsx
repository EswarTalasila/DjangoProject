'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

import { Button } from '@/components/ui/button';

export default function ResearcherView() {
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Researcher Dashboard
        </h1>
        <p className="text-muted-foreground mt-1">
          Build assessment templates, manage teacher-facing setup, and review anonymized analytics.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-sm border border-border bg-card p-6">
          <h2 className="text-lg font-semibold text-foreground">Assessments & Rubrics</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Create and maintain templates teachers use when building assignments.
          </p>
          <div className="mt-4 flex gap-2 flex-wrap">
            <Button asChild>
              <Link href="/dashboard/assessments">
                Open Assessments
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/dashboard/rubrics">Open Rubrics</Link>
            </Button>
          </div>
        </div>

        <div className="rounded-sm border border-border bg-card p-6">
          <h2 className="text-lg font-semibold text-foreground">Teacher Operations</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Manage teacher roster and issue registration/password reset workflows.
          </p>
          <div className="mt-4 flex gap-2 flex-wrap">
            <Button asChild>
              <Link href="/dashboard/staff">Open User Management</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/dashboard/codes">Open Registration Codes</Link>
            </Button>
          </div>
        </div>

        <div className="rounded-sm border border-border bg-card p-6 md:col-span-2">
          <h2 className="text-lg font-semibold text-foreground">Analytics</h2>
          <p className="text-sm text-muted-foreground mt-1">
            View anonymized visualization summaries for courses and assignments.
          </p>
          <div className="mt-4">
            <Button asChild variant="outline">
              <Link href="/dashboard/visualizations">
                Open Visualizations
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
