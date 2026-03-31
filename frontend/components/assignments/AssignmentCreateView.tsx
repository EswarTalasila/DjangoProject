'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { createAssignment } from '@/lib/assignment-api';
import { listAssessments, type Assessment } from '@/lib/assessment-api';
import { listCourses, type CourseSummary } from '@/lib/course-api';
import { toErrorMessage } from '@/lib/utils';

function toDateTimeLocal(value: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}T${pad(value.getHours())}:${pad(value.getMinutes())}`;
}

function toIsoOrNull(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

export default function AssignmentCreateView() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [title, setTitle] = useState('');
  const [assessmentId, setAssessmentId] = useState('');
  const [courseId, setCourseId] = useState('');
  const [openAt, setOpenAt] = useState('');
  const [dueAt, setDueAt] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoadError(null);
      try {
        const [assessmentData, courseData] = await Promise.all([listAssessments(), listCourses()]);
        if (cancelled) return;

        setAssessments(assessmentData);
        setCourses(courseData);
        const firstAssessment = assessmentData[0];
        setAssessmentId(String(firstAssessment?.id ?? ''));
        setTitle(firstAssessment?.title ?? '');
        const preferredCourseId = searchParams.get('courseId');
        const hasPreferred =
          preferredCourseId != null &&
          courseData.some((course) => String(course.id) === preferredCourseId);
        setCourseId(
          hasPreferred ? preferredCourseId : String(courseData[0]?.id ?? ''),
        );

        const now = new Date();
        const plusWeek = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
        setOpenAt(toDateTimeLocal(now));
        setDueAt(toDateTimeLocal(plusWeek));
      } catch {
        if (!cancelled) setLoadError('Failed to load assignment form data.');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  const canSubmit = useMemo(() => {
    return Boolean(title.trim() && assessmentId && courseId && openAt);
  }, [title, assessmentId, courseId, openAt]);

  function handleAssessmentChange(nextAssessmentId: string) {
    setAssessmentId(nextAssessmentId);
    const selected = assessments.find((assessment) => String(assessment.id) === nextAssessmentId);
    if (selected) {
      setTitle(selected.title);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;

    const openIso = toIsoOrNull(openAt);
    const dueIso = toIsoOrNull(dueAt);
    if (!openIso) {
      toast.error('Please provide a valid open date/time.');
      return;
    }
    if (dueIso && openIso >= dueIso) {
      toast.error('Open time must be before due time.');
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await createAssignment({
        title: title.trim(),
        assessmentId: Number(assessmentId),
        audienceType: 'COURSE',
        courseId: Number(courseId),
        openAt: openIso,
        dueAt: dueIso,
      });
      toast.success('Assignment created.');
      router.push(`/dashboard/assignments/${created.id}`);
    } catch (error: unknown) {
      if ((error as { response?: { status?: number } }).response?.status === 409) {
        toast.error('Cannot create assignment from archived assessment.');
      } else {
        toast.error(toErrorMessage(error, 'Failed to create assignment.'));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Create Assignment</h1>
        <p className="text-muted-foreground mt-1">
          Link an assessment template to one of your courses.
        </p>
      </div>

      {loadError && <p className="text-sm text-destructive">{loadError}</p>}

      <form onSubmit={handleSubmit} className="rounded-sm border border-border bg-card p-6 space-y-4">
        <div className="space-y-2">
          <Label htmlFor="assignment-title">Assignment Title</Label>
          <Input
            id="assignment-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="e.g. Week 3 Check-In"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="assessment-id">Assessment</Label>
          <Select value={assessmentId} onValueChange={handleAssessmentChange}>
            <SelectTrigger id="assessment-id">
              <SelectValue placeholder="Select assessment" />
            </SelectTrigger>
            <SelectContent>
              {assessments.map((assessment) => (
                <SelectItem key={assessment.id} value={String(assessment.id)}>
                  {assessment.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="course-id">Course</Label>
          <Select value={courseId} onValueChange={setCourseId}>
            <SelectTrigger id="course-id">
              <SelectValue placeholder="Select course" />
            </SelectTrigger>
            <SelectContent>
              {courses.map((course) => (
                <SelectItem key={course.id} value={String(course.id)}>
                  {course.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="open-at">Open At</Label>
            <Input
              id="open-at"
              type="datetime-local"
              value={openAt}
              onChange={(event) => setOpenAt(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="due-at">Due At</Label>
            <Input
              id="due-at"
              type="datetime-local"
              value={dueAt}
              onChange={(event) => setDueAt(event.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={isSubmitting || !canSubmit}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Create Assignment
          </Button>
          <Button type="button" variant="outline" onClick={() => router.push('/dashboard/assignments')}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
