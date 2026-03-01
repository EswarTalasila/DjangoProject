'use client';

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { BookOpen, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { listCourses, type CourseSummary } from '@/lib/course-api';
import { joinCourseByCode } from '@/lib/registration-code-api';

type ApiError = { response?: { data?: { detail?: string } } };

const joinCourseSchema = z.object({
  code: z.string().min(1, 'Course code is required').max(64),
});

type JoinCourseForm = z.infer<typeof joinCourseSchema>;

export default function StudentView() {
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
    reset,
  } = useForm<JoinCourseForm>({
    resolver: zodResolver(joinCourseSchema),
    defaultValues: { code: '' },
  });

  async function loadCourses() {
    setLoadError(null);
    try {
      const data = await listCourses();
      setCourses(data);
    } catch {
      setLoadError('Failed to load courses.');
    } finally {
      setIsBootstrapping(false);
    }
  }

  useEffect(() => {
    void loadCourses();
  }, []);

  async function onSubmit(data: JoinCourseForm) {
    try {
      const result = await joinCourseByCode(data.code.trim());
      if (result.alreadyEnrolled) {
        toast.info('You are already enrolled in this course.');
      } else {
        toast.success('Successfully joined the course!');
      }
      reset();
      await loadCourses();
    } catch (error: unknown) {
      const detail = (error as ApiError).response?.data?.detail;
      setError('code', {
        type: 'manual',
        message: detail || 'Invalid or expired course code.',
      });
    }
  }

  return (
    <div className="space-y-8 p-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-[#61323e]">Student Dashboard</h1>
        <p className="text-[#754d28] mt-1">Join courses and view your enrollments.</p>
      </div>

      <Card className="border-[#ebe9e7] shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg text-[#2b6ea4]">Join a Course</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="flex items-end gap-3">
            <div className="flex-1 space-y-2">
              <Label htmlFor="code">Course Code</Label>
              <Input
                id="code"
                placeholder="Enter your course code"
                className="border-[#ebe9e7] focus-visible:ring-[#2b6ea4]"
                disabled={isSubmitting}
                {...register('code')}
              />
              {errors.code ? (
                <p className="text-sm text-red-600">{errors.code.message}</p>
              ) : null}
            </div>
            <Button
              type="submit"
              className="bg-[#2b6ea4] hover:bg-[#205a86] text-white"
              disabled={isSubmitting}
            >
              {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Join
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-[#61323e]">My Courses</h2>

        {loadError ? <p className="text-sm text-red-600">{loadError}</p> : null}
        {isBootstrapping ? <p className="text-sm text-[#754d28]">Loading courses...</p> : null}

        {!isBootstrapping && !courses.length ? (
          <Card className="border-[#ebe9e7] border-dashed">
            <CardContent className="py-8 text-center">
              <BookOpen className="mx-auto h-10 w-10 text-[#754d28] opacity-40 mb-3" />
              <p className="text-sm text-[#754d28]">
                No courses yet. Enter a course code above to get started.
              </p>
            </CardContent>
          </Card>
        ) : null}

        {!isBootstrapping && courses.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            {courses.map((course) => (
              <Card
                key={course.id}
                className="border-[#ebe9e7] hover:border-[#2b6ea4] transition-colors"
              >
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg font-semibold text-[#2b6ea4]">
                    {course.name}
                  </CardTitle>
                  <p className="text-sm text-[#754d28] mt-1 font-mono bg-[#eff6f7] px-2 py-0.5 rounded inline-block">
                    Course #{course.id}
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="text-sm text-[#754d28] border-t border-[#ebe9e7] pt-3">
                    Enrolled
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
