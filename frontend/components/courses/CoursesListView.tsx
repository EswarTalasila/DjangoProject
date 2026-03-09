'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, Plus, Search } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  createCourse,
  listCourses,
  type CourseSummary,
} from '@/lib/course-api';
import { joinCourseByCode } from '@/lib/registration-code-api';

type ApiError = { response?: { data?: { detail?: string } } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

function formatDate(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

type CoursesListViewProps = {
  userRole: 'TEACHER' | 'RESEARCHER' | 'STUDENT';
};

export default function CoursesListView({ userRole }: CoursesListViewProps) {
  const router = useRouter();

  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newCourseName, setNewCourseName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const canCreate = userRole === 'TEACHER';

  const joinSchema = z.object({
    code: z.string().min(1, 'Course code is required').max(64),
  });
  type JoinForm = z.infer<typeof joinSchema>;

  const {
    register: registerJoin,
    handleSubmit: handleJoinSubmit,
    formState: { errors: joinErrors, isSubmitting: isJoining },
    setError: setJoinError,
    reset: resetJoin,
  } = useForm<JoinForm>({
    resolver: zodResolver(joinSchema),
    defaultValues: { code: '' },
  });

  const loadCourses = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await listCourses();
      setCourses(data);
    } catch {
      setLoadError('Failed to load courses.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  async function onJoinSubmit(data: JoinForm) {
    try {
      const result = await joinCourseByCode(data.code.trim());
      if (result.alreadyEnrolled) {
        toast.info('You are already enrolled in this course.');
      } else {
        toast.success('Successfully joined the course!');
      }
      resetJoin();
      await loadCourses();
    } catch (error: unknown) {
      setJoinError('code', {
        type: 'manual',
        message: extractDetail(error, 'Invalid or expired course code.'),
      });
    }
  }

  useEffect(() => {
    setIsLoading(true);
    void loadCourses();
  }, [loadCourses]);

  const filteredCourses = useMemo(() => {
    if (!searchQuery.trim()) return courses;
    const query = searchQuery.toLowerCase();
    return courses.filter(
      (course) =>
        course.name.toLowerCase().includes(query) ||
        (course.teacherName && course.teacherName.toLowerCase().includes(query))
    );
  }, [courses, searchQuery]);

  async function handleCreateCourse() {
    const trimmed = newCourseName.trim();
    if (!trimmed) return;

    setIsCreating(true);
    try {
      await createCourse(trimmed);
      toast.success(`Course "${trimmed}" created.`);
      setIsCreateDialogOpen(false);
      setNewCourseName('');
      await loadCourses();
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to create course.'));
    } finally {
      setIsCreating(false);
    }
  }

  function handleRowClick(courseId: number) {
    router.push(`/dashboard/courses/${courseId}`);
  }

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Course</DialogTitle>
            <DialogDescription>
              Enter a name for the new course.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="course-name">Course Name</Label>
            <Input
              id="course-name"
              placeholder="e.g. Physics 101"
              value={newCourseName}
              onChange={(e) => setNewCourseName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !isCreating) {
                  void handleCreateCourse();
                }
              }}
              disabled={isCreating}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsCreateDialogOpen(false)}
              disabled={isCreating}
            >
              Cancel
            </Button>
            <Button
              onClick={() => void handleCreateCourse()}
              disabled={isCreating || !newCourseName.trim()}
            >
              {isCreating ? 'Creating...' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            Courses
          </h1>
          <p className="text-muted-foreground mt-1">
            {canCreate
              ? 'Manage your courses and enrolled students.'
              : userRole === 'STUDENT'
                ? 'View your enrolled courses or join a new one.'
                : 'View courses and enrolled students.'}
          </p>
        </div>
        {canCreate && (
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Course
          </Button>
        )}
      </div>

      {userRole === 'STUDENT' && (
        <Card className="border-border shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg text-primary">Join a Course</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleJoinSubmit(onJoinSubmit)} className="flex items-end gap-3">
              <div className="flex-1 space-y-2">
                <Label htmlFor="join-code">Course Code</Label>
                <Input
                  id="join-code"
                  placeholder="Enter your course code"
                  className="border-border focus-visible:ring-ring"
                  disabled={isJoining}
                  {...registerJoin('code')}
                />
                {joinErrors.code ? (
                  <p className="text-sm text-destructive">{joinErrors.code.message}</p>
                ) : null}
              </div>
              <Button
                type="submit"
                className="bg-primary hover:bg-primary/90 text-primary-foreground"
                disabled={isJoining}
              >
                {isJoining ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Join
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search courses..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      {loadError && (
        <p className="text-sm text-destructive">{loadError}</p>
      )}

      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading courses...</p>
      )}

      {!isLoading && !loadError && filteredCourses.length === 0 && (
        <div className="rounded-sm border border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            {courses.length === 0
              ? canCreate
                ? 'No courses yet. Create your first course to get started.'
                : 'No courses found.'
              : 'No courses match your search.'}
          </p>
        </div>
      )}

      {!isLoading && !loadError && filteredCourses.length > 0 && (
        <div className="rounded-sm border border-border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted border-b border-border">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Course Name
                </TableHead>
                {userRole !== 'STUDENT' && (
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Teacher
                  </TableHead>
                )}
                {userRole !== 'STUDENT' && (
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Students
                  </TableHead>
                )}
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Created
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCourses.map((course) => (
                <TableRow
                  key={course.id}
                  className="even:bg-muted/50 hover:bg-accent transition-colors cursor-pointer"
                  onClick={() => handleRowClick(course.id)}
                >
                  <TableCell className="font-medium text-sm text-foreground">
                    {course.name}
                  </TableCell>
                  {userRole !== 'STUDENT' && (
                    <TableCell className="text-sm text-muted-foreground">
                      {course.teacherName ?? '-'}
                    </TableCell>
                  )}
                  {userRole !== 'STUDENT' && (
                    <TableCell className="text-sm text-muted-foreground">
                      {course.studentCount}
                    </TableCell>
                  )}
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(course.createdAt)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
