'use client';

import { useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { toast } from 'sonner';

import { ResetCodeDialog } from '@/components/codes/ResetCodeDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  issuePasswordResetCode,
  listStaffUsers,
  listStudents,
  type StaffUser,
  type StudentUser,
} from '@/lib/password-reset-api';
import { listCourses, type CourseSummary } from '@/lib/course-api';

type Tab = 'teachers' | 'students' | 'researchers';
type ApiError = { response?: { data?: { detail?: string } } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

type StaffManagementViewProps = {
  canResetStudents: boolean;
  canResetResearchers: boolean;
};

export default function StaffManagementView({ canResetStudents, canResetResearchers }: StaffManagementViewProps) {
  const [activeTab, setActiveTab] = useState<Tab>('teachers');
  const [search, setSearch] = useState('');
  const [courseFilter, setCourseFilter] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isActionLoading, setIsActionLoading] = useState(false);

  const [teachers, setTeachers] = useState<StaffUser[]>([]);
  const [researchers, setResearchers] = useState<StaffUser[]>([]);
  const [students, setStudents] = useState<StudentUser[]>([]);
  const [courses, setCourses] = useState<CourseSummary[]>([]);

  const [resetCode, setResetCode] = useState<string | null>(null);
  const [resetTargetName, setResetTargetName] = useState<string | null>(null);
  const [resetExpiresAt, setResetExpiresAt] = useState<string | null>(null);
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setLoadError(null);
      try {
        const [staffData, courseData] = await Promise.all([
          listStaffUsers(),
          listCourses(),
        ]);
        setTeachers(staffData.filter((u) => u.role === 'TEACHER'));
        if (canResetResearchers) {
          setResearchers(staffData.filter((u) => u.role === 'RESEARCHER'));
        }
        setCourses(courseData);
        if (canResetStudents) {
          const studentData = await listStudents();
          setStudents(studentData);
        }
      } catch {
        setLoadError('Failed to load staff data.');
      } finally {
        setIsLoading(false);
      }
    }
    void load();
  }, []);

  useEffect(() => {
    if (activeTab !== 'students' || !canResetStudents) return;
    async function reload() {
      setIsLoading(true);
      try {
        const data = await listStudents(
          courseFilter ? { courseId: courseFilter } : undefined,
        );
        setStudents(data);
      } catch {
        setLoadError('Failed to load students.');
      } finally {
        setIsLoading(false);
      }
    }
    void reload();
  }, [courseFilter, activeTab, canResetStudents]);

  const filteredTeachers = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return teachers;
    return teachers.filter(
      (t) =>
        t.name.toLowerCase().includes(needle) ||
        t.username.toLowerCase().includes(needle) ||
        (t.email || '').toLowerCase().includes(needle),
    );
  }, [teachers, search]);

  const filteredResearchers = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return researchers;
    return researchers.filter(
      (r) =>
        r.name.toLowerCase().includes(needle) ||
        r.username.toLowerCase().includes(needle) ||
        (r.email || '').toLowerCase().includes(needle),
    );
  }, [researchers, search]);

  const filteredStudents = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return students;
    return students.filter(
      (s) =>
        s.name.toLowerCase().includes(needle) ||
        s.username.toLowerCase().includes(needle),
    );
  }, [students, search]);

  async function handleIssueReset(targetId: number, targetName: string) {
    setIsActionLoading(true);
    try {
      const response = await issuePasswordResetCode(targetId);
      setResetCode(response.resetCode);
      setResetTargetName(targetName);
      setResetExpiresAt(response.expiresAt);
      setIsResetDialogOpen(true);
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to issue reset code.'));
    } finally {
      setIsActionLoading(false);
    }
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'teachers', label: 'Teachers' },
    ...(canResetStudents ? [{ key: 'students' as Tab, label: 'Students' }] : []),
    ...(canResetResearchers ? [{ key: 'researchers' as Tab, label: 'Researchers' }] : []),
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <ResetCodeDialog
        open={isResetDialogOpen}
        onOpenChange={setIsResetDialogOpen}
        code={resetCode}
        targetName={resetTargetName}
        expiresAt={resetExpiresAt}
      />

      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          User Management
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage accounts and issue password reset codes.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => {
              setActiveTab(tab.key);
              setSearch('');
            }}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={`Search ${activeTab}...`}
            className="pl-8 border-border focus-visible:ring-ring"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {activeTab === 'students' && (
          <select
            className="rounded-sm border border-border bg-background px-3 py-2 text-sm text-foreground"
            value={courseFilter ?? ''}
            onChange={(e) =>
              setCourseFilter(e.target.value ? Number(e.target.value) : null)
            }
          >
            <option value="">All Courses</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Error / Loading */}
      {loadError && <p className="text-sm text-destructive">{loadError}</p>}
      {isLoading && <p className="text-sm text-muted-foreground">Loading...</p>}

      {/* Teachers Table */}
      {activeTab === 'teachers' && !isLoading && (
        <div className="rounded-sm border border-border overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted border-b border-border">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Name</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Email</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Username</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTeachers.length === 0 && (
                <tr><td colSpan={4} className="px-4 py-6 text-center text-sm text-muted-foreground">No teachers found.</td></tr>
              )}
              {filteredTeachers.map((teacher) => (
                <tr key={teacher.id} className="even:bg-muted/50 hover:bg-accent transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-foreground">{teacher.name}</td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{teacher.email || '-'}</td>
                  <td className="px-4 py-3 text-sm text-foreground font-mono">@{teacher.username}</td>
                  <td className="px-4 py-3">
                    <Button size="sm" variant="outline" disabled={isActionLoading} onClick={() => void handleIssueReset(teacher.id, teacher.name)}>
                      Issue Reset
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Researchers Table */}
      {activeTab === 'researchers' && !isLoading && (
        <div className="rounded-sm border border-border overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted border-b border-border">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Name</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Email</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Username</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredResearchers.length === 0 && (
                <tr><td colSpan={4} className="px-4 py-6 text-center text-sm text-muted-foreground">No researchers found.</td></tr>
              )}
              {filteredResearchers.map((researcher) => (
                <tr key={researcher.id} className="even:bg-muted/50 hover:bg-accent transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-foreground">{researcher.name}</td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{researcher.email || '-'}</td>
                  <td className="px-4 py-3 text-sm text-foreground font-mono">@{researcher.username}</td>
                  <td className="px-4 py-3">
                    <Button size="sm" variant="outline" disabled={isActionLoading} onClick={() => void handleIssueReset(researcher.id, researcher.name)}>
                      Issue Reset
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Students Table */}
      {activeTab === 'students' && !isLoading && (
        <div className="rounded-sm border border-border overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted border-b border-border">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Name</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Username</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Courses</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredStudents.length === 0 && (
                <tr><td colSpan={4} className="px-4 py-6 text-center text-sm text-muted-foreground">No students found.</td></tr>
              )}
              {filteredStudents.map((student) => (
                <tr key={student.id} className="even:bg-muted/50 hover:bg-accent transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-foreground">{student.name}</td>
                  <td className="px-4 py-3 text-sm text-foreground font-mono">@{student.username}</td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {student.courses.length > 0
                      ? student.courses.map((c) => c.name).join(', ')
                      : 'No courses'}
                  </td>
                  <td className="px-4 py-3">
                    <Button size="sm" variant="outline" disabled={isActionLoading} onClick={() => void handleIssueReset(student.id, student.name)}>
                      Issue Reset
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
