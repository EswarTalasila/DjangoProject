'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  MoreVertical,
  Plus,
  Search,
} from 'lucide-react';
import { toast } from 'sonner';

import { ResetCodeDialog } from '@/components/codes/ResetCodeDialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { createCourse, listCourses, type CourseSummary } from '@/lib/course-api';
import { cn } from '@/lib/utils';
import {
  issuePasswordResetCode,
  listStudentsInCourse,
  type CourseStudent,
} from '@/lib/password-reset-api';

type ApiError = { response?: { data?: { detail?: string } } };

function extractDetail(error: unknown, fallback: string): string {
  const detail = (error as ApiError).response?.data?.detail;
  return detail || fallback;
}

export default function TeacherView() {
  const [isLoading, setIsLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [expandedCourseIds, setExpandedCourseIds] = useState<number[]>([]);
  const [studentsByCourse, setStudentsByCourse] = useState<Record<number, CourseStudent[]>>({});
  const [isStudentsLoading, setIsStudentsLoading] = useState<Record<number, boolean>>({});

  const [resetCode, setResetCode] = useState<string | null>(null);
  const [resetTargetName, setResetTargetName] = useState<string | null>(null);
  const [resetExpiresAt, setResetExpiresAt] = useState<string | null>(null);
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);

  const filteredCourses = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return courses;
    return courses.filter((course) => course.name.toLowerCase().includes(needle));
  }, [courses, search]);

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

  async function handleCreateCourse() {
    const name = window.prompt('Course name');
    if (!name || !name.trim()) return;

    setIsLoading(true);
    try {
      await createCourse(name.trim());
      toast.success('Course created.');
      await loadCourses();
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to create course.'));
    } finally {
      setIsLoading(false);
    }
  }

  async function toggleStudents(courseId: number) {
    const isExpanded = expandedCourseIds.includes(courseId);
    if (isExpanded) {
      setExpandedCourseIds((prev) => prev.filter((id) => id !== courseId));
      return;
    }

    setExpandedCourseIds((prev) => [...prev, courseId]);
    if (studentsByCourse[courseId] !== undefined) return;

    setIsStudentsLoading((prev) => ({ ...prev, [courseId]: true }));
    try {
      const students = await listStudentsInCourse(courseId);
      setStudentsByCourse((prev) => ({ ...prev, [courseId]: students }));
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to load students.'));
    } finally {
      setIsStudentsLoading((prev) => ({ ...prev, [courseId]: false }));
    }
  }

  async function handleIssueResetCode(student: CourseStudent) {
    setIsLoading(true);
    try {
      const response = await issuePasswordResetCode(student.id);
      setResetCode(response.resetCode);
      setResetTargetName(student.name);
      setResetExpiresAt(response.expiresAt);
      setIsResetDialogOpen(true);
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to issue reset code.'));
    } finally {
      setIsLoading(false);
    }
  }

  const totalStudents = courses.reduce((sum, course) => sum + course.studentCount, 0);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <ResetCodeDialog
        open={isResetDialogOpen}
        onOpenChange={setIsResetDialogOpen}
        code={resetCode}
        targetName={resetTargetName}
        expiresAt={resetExpiresAt}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Teacher Dashboard</h1>
          <p className="text-muted-foreground mt-1">Manage your courses and issue student reset codes.</p>
        </div>
        <Button
          className="bg-primary hover:bg-primary/90 text-primary-foreground"
          onClick={handleCreateCourse}
          disabled={isLoading}
        >
          <Plus className="mr-2 h-4 w-4" />
          Create New Course
        </Button>
      </div>

      <div className="flex items-center gap-0 divide-x divide-border bg-muted px-4 py-3 rounded-sm">
        {[
          { label: 'Students', value: totalStudents },
          { label: 'Active Courses', value: courses.length },
          { label: 'Pending Grades', value: '\u2014' },
        ].map((stat) => (
          <div key={stat.label} className="flex items-baseline gap-2 px-6 first:pl-0 last:pr-0">
            <span className="text-2xl font-bold text-foreground">{stat.value}</span>
            <span className="text-sm text-muted-foreground">{stat.label}</span>
          </div>
        ))}
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-foreground">Your Courses</h2>
          <div className="relative w-64">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search courses..."
              className="pl-8 border-border focus-visible:ring-ring"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        {loadError ? <p className="text-sm text-destructive">{loadError}</p> : null}
        {isBootstrapping ? <p className="text-sm text-muted-foreground">Loading courses...</p> : null}
        {!isBootstrapping && !filteredCourses.length ? (
          <p className="text-sm text-muted-foreground">No courses found.</p>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredCourses.map((course) => {
            const isExpanded = expandedCourseIds.includes(course.id);
            const students = studentsByCourse[course.id] ?? [];
            const isLoadingStudents = Boolean(isStudentsLoading[course.id]);
            return (
              <Card
                key={course.id}
                className="border-border hover:border-primary transition-colors group"
              >
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-lg text-primary font-semibold">
                        {course.name}
                      </CardTitle>
                      <p className="text-xs text-muted-foreground font-mono bg-muted px-2 py-0.5 inline-block mt-1">
                        Course #{course.id}
                      </p>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="h-8 w-8 p-0 text-muted-foreground" disabled={isLoading}>
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => void toggleStudents(course.id)}>
                          {isExpanded ? 'Hide Students' : 'View Students'}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex justify-between text-sm text-muted-foreground border-t border-border pt-3 mt-1">
                    <div className="flex items-center">
                      {course.studentCount} Students
                    </div>
                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => void toggleStudents(course.id)}>
                      {isExpanded ? (
                        <>
                          <ChevronUp className="mr-1 h-4 w-4" />
                          Hide
                        </>
                      ) : (
                        <>
                          <ChevronDown className="mr-1 h-4 w-4" />
                          Students
                        </>
                      )}
                    </Button>
                  </div>

                  {isExpanded ? (
                    <div className="mt-3 border-t border-border pt-3">
                      {isLoadingStudents ? (
                        <p className="text-xs text-muted-foreground">Loading students...</p>
                      ) : students.length ? (
                        <table className="w-full text-sm">
                          <tbody>
                            {students.map((student, i) => (
                              <tr key={student.id} className={cn("transition-colors", i % 2 === 1 && "bg-muted/50")}>
                                <td className="py-2 pr-3">
                                  <p className="font-medium text-foreground">{student.name}</p>
                                  <p className="text-xs text-muted-foreground">@{student.username}</p>
                                </td>
                                <td className="py-2 text-right">
                                  <Button size="sm" variant="outline" disabled={isLoading} onClick={() => void handleIssueResetCode(student)}>
                                    Issue Reset
                                  </Button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : (
                        <p className="text-xs text-muted-foreground">No students enrolled.</p>
                      )}
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
