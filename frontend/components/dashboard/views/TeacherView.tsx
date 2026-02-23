'use client';

import { useEffect, useMemo, useState } from 'react';
import { BookOpen, ClipboardCheck, MoreVertical, Plus, Search, Users } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { RegistrationCodeDialog } from '@/components/codes/RegistrationCodeDialog';
import { createCourse, listCourses, type CourseSummary } from '@/lib/course-api';
import { createStudentRegistrationCode } from '@/lib/registration-code-api';

export default function TeacherView() {
  const [isLoading, setIsLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [registrationCode, setRegistrationCode] = useState<string | null>(null);
  const [isCodeDialogOpen, setIsCodeDialogOpen] = useState(false);

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
      const detail =
        typeof error === 'object' &&
        error !== null &&
        'response' in error &&
        typeof (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ===
          'string'
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : 'Failed to create course.';
      toast.error(detail);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleGenerateInviteCode(courseId: number) {
    setIsLoading(true);
    try {
      const code = await createStudentRegistrationCode(courseId);
      setRegistrationCode(code);
      setIsCodeDialogOpen(true);
    } catch (error: unknown) {
      const detail =
        typeof error === 'object' &&
        error !== null &&
        'response' in error &&
        typeof (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ===
          'string'
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : 'Failed to generate invite code.';
      toast.error(detail);
    } finally {
      setIsLoading(false);
    }
  }

  const totalStudents = courses.reduce((sum, course) => sum + course.studentCount, 0);
  const stats = [
    { label: 'Total Students', value: String(totalStudents), icon: Users, color: 'text-[#2b6ea4]' },
    { label: 'Active Courses', value: String(courses.length), icon: BookOpen, color: 'text-[#61323e]' },
    { label: 'Pending Grades', value: 'N/A', icon: ClipboardCheck, color: 'text-[#754d28]' },
  ];

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      <RegistrationCodeDialog
        open={isCodeDialogOpen}
        onOpenChange={setIsCodeDialogOpen}
        code={registrationCode}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[#61323e]">Teacher Dashboard</h1>
          <p className="text-[#754d28] mt-1">Manage your courses, assignments, and student grades.</p>
        </div>
        <Button
          className="bg-[#2b6ea4] hover:bg-[#205a86] text-white"
          onClick={handleCreateCourse}
          disabled={isLoading}
        >
          <Plus className="mr-2 h-4 w-4" />
          Create New Course
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {stats.map((stat) => (
          <Card key={stat.label} className="border-[#ebe9e7] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-[#754d28]">{stat.label}</CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-[#61323e]">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[#61323e]">Your Courses</h2>
          <div className="relative w-64">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-[#754d28]" />
            <Input
              placeholder="Search courses..."
              className="pl-8 border-[#ebe9e7] focus-visible:ring-[#2b6ea4]"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        {loadError ? <p className="text-sm text-red-600">{loadError}</p> : null}
        {isBootstrapping ? <p className="text-sm text-[#754d28]">Loading courses...</p> : null}

        {!isBootstrapping && !filteredCourses.length ? (
          <p className="text-sm text-[#754d28]">No courses found.</p>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredCourses.map((course) => (
            <Card
              key={course.id}
              className="border-[#ebe9e7] hover:border-[#2b6ea4] transition-colors cursor-pointer group"
            >
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg font-semibold text-[#2b6ea4] group-hover:underline decoration-[#2b6ea4] underline-offset-4">
                      {course.name}
                    </CardTitle>
                    <p className="text-sm text-[#754d28] mt-1 font-mono bg-[#eff6f7] px-2 py-0.5 rounded inline-block">
                      Course #{course.id}
                    </p>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" className="h-8 w-8 p-0 text-[#754d28]" disabled={isLoading}>
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleGenerateInviteCode(course.id)}>
                        Generate Invite Code
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between text-sm text-[#754d28] border-t border-[#ebe9e7] pt-4 mt-2">
                  <div className="flex items-center">
                    <Users className="mr-1 h-4 w-4 opacity-70" />
                    {course.studentCount} Students
                  </div>
                  <div className="flex items-center font-medium text-[#61323e]">
                    <ClipboardCheck className="mr-1 h-4 w-4 opacity-70" />
                    {course.assignmentIds.length} assignments
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
