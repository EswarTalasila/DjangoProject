'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  MoreVertical,
  Plus,
  Search,
  Users,
} from 'lucide-react';
import { toast } from 'sonner';

import { CreateRegistrationCodeDialog } from '@/components/codes/CreateRegistrationCodeDialog';
import { ResetCodeDialog } from '@/components/codes/ResetCodeDialog';
import { RegistrationCodeDialog } from '@/components/codes/RegistrationCodeDialog';
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
import {
  issuePasswordResetCode,
  listStudentsInCourse,
  type CourseStudent,
} from '@/lib/password-reset-api';
import { createRegistrationCodes } from '@/lib/registration-code-api';

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
  const [registrationCodes, setRegistrationCodes] = useState<string[]>([]);
  const [isCodeDialogOpen, setIsCodeDialogOpen] = useState(false);
  const [isCreateCodeDialogOpen, setIsCreateCodeDialogOpen] = useState(false);
  const [selectedCourseIdForCode, setSelectedCourseIdForCode] = useState<number | null>(null);

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

  function handleOpenGenerateInviteCode(courseId: number) {
    setSelectedCourseIdForCode(courseId);
    setIsCreateCodeDialogOpen(true);
  }

  async function handleGenerateInviteCode(config: {
    count: number;
    usesPerCode: number;
    expiresAt: string;
  }) {
    if (!selectedCourseIdForCode) return;
    setIsLoading(true);
    try {
      const response = await createRegistrationCodes({
        codeType: 'STUDENT',
        count: config.count,
        usesPerCode: config.usesPerCode,
        expiresAt: config.expiresAt,
        courseId: selectedCourseIdForCode,
      });
      const plainCodes = response.codes
        .map((c) => c.code)
        .filter((c): c is string => c != null);
      if (plainCodes.length === 0) throw new Error('Registration code was not returned by the server.');
      setRegistrationCodes(plainCodes);
      setIsCreateCodeDialogOpen(false);
      setIsCodeDialogOpen(true);
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to generate invite code.'));
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
  const stats = [
    { label: 'Total Students', value: String(totalStudents), icon: Users, color: 'text-[#2b6ea4]' },
    { label: 'Active Courses', value: String(courses.length), icon: BookOpen, color: 'text-[#61323e]' },
    { label: 'Pending Grades', value: 'N/A', icon: ClipboardCheck, color: 'text-[#754d28]' },
  ];

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      <CreateRegistrationCodeDialog
        open={isCreateCodeDialogOpen}
        onOpenChange={setIsCreateCodeDialogOpen}
        isLoading={isLoading}
        title="Generate student invite code"
        description="Set usage count and expiration before creating the code."
        allowedCodeTypes={['STUDENT']}
        initialCodeType="STUDENT"
        hideCodeType
        onSubmit={async (values) =>
          handleGenerateInviteCode({
            count: values.count,
            usesPerCode: values.usesPerCode,
            expiresAt: values.expiresAt,
          })
        }
      />
      <RegistrationCodeDialog
        open={isCodeDialogOpen}
        onOpenChange={setIsCodeDialogOpen}
        codes={registrationCodes}
      />
      <ResetCodeDialog
        open={isResetDialogOpen}
        onOpenChange={setIsResetDialogOpen}
        code={resetCode}
        targetName={resetTargetName}
        expiresAt={resetExpiresAt}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[#61323e]">Teacher Dashboard</h1>
          <p className="text-[#754d28] mt-1">Manage your courses and issue student reset codes.</p>
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
          {filteredCourses.map((course) => {
            const isExpanded = expandedCourseIds.includes(course.id);
            const students = studentsByCourse[course.id] ?? [];
            const isLoadingStudents = Boolean(isStudentsLoading[course.id]);
            return (
              <Card
                key={course.id}
                className="border-[#ebe9e7] hover:border-[#2b6ea4] transition-colors group"
              >
                <CardHeader className="pb-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-lg font-semibold text-[#2b6ea4]">
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
                        <DropdownMenuItem onClick={() => handleOpenGenerateInviteCode(course.id)}>
                          Generate Invite Code
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => void toggleStudents(course.id)}>
                          {isExpanded ? 'Hide Students' : 'View Students'}
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
                    <Button variant="ghost" size="sm" onClick={() => void toggleStudents(course.id)}>
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
                    <div className="mt-4 border-t border-[#ebe9e7] pt-3">
                      {isLoadingStudents ? (
                        <p className="text-xs text-[#754d28]">Loading students...</p>
                      ) : students.length ? (
                        <div className="space-y-2">
                          {students.map((student) => (
                            <div
                              key={student.id}
                              className="flex items-center justify-between rounded border border-[#ebe9e7] p-2"
                            >
                              <div>
                                <p className="text-sm font-medium text-[#61323e]">{student.name}</p>
                                <p className="text-xs text-[#754d28]">@{student.username}</p>
                              </div>
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={isLoading}
                                onClick={() => void handleIssueResetCode(student)}
                              >
                                Issue Reset
                              </Button>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-[#754d28]">No students enrolled.</p>
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
