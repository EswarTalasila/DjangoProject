'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Search } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  listAssignmentsByCourse,
  listAssignmentsForUser,
  type Assignment,
} from '@/lib/assignment-api';
import { listAssessments } from '@/lib/assessment-api';
import { listCourses, type CourseSummary } from '@/lib/course-api';

type Role = 'TEACHER' | 'RESEARCHER' | 'ADMIN';

type AssessmentLite = {
  id: number;
  title: string;
};

type AssignmentListViewProps = {
  role: Role;
  userId: string;
  canCreate: boolean;
};

function formatDate(value: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

export default function AssignmentListView({ role, userId, canCreate }: AssignmentListViewProps) {
  const router = useRouter();

  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [assessmentMap, setAssessmentMap] = useState<Map<number, AssessmentLite>>(new Map());
  const [selectedCourseId, setSelectedCourseId] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoadError(null);
    try {
      const [courseData, assessments] = await Promise.all([listCourses(), listAssessments()]);
      setCourses(courseData);
      setAssessmentMap(new Map(assessments.map((a) => [a.id, { id: a.id, title: a.title }])));

      if (role === 'TEACHER') {
        const items = await listAssignmentsForUser(userId);
        setAssignments(items);
      } else {
        const defaultCourseId = selectedCourseId || String(courseData[0]?.id ?? '');
        setSelectedCourseId(defaultCourseId);
        if (defaultCourseId) {
          const items = await listAssignmentsByCourse(Number(defaultCourseId));
          setAssignments(items);
        } else {
          setAssignments([]);
        }
      }
    } catch {
      setLoadError('Failed to load assignments.');
    } finally {
      setIsLoading(false);
    }
  }, [role, selectedCourseId, userId]);

  useEffect(() => {
    setIsLoading(true);
    void loadData();
  }, [loadData]);

  async function handleCourseChange(nextCourseId: string) {
    setSelectedCourseId(nextCourseId);
    if (!nextCourseId) {
      setAssignments([]);
      return;
    }
    setIsLoading(true);
    setLoadError(null);
    try {
      const items = await listAssignmentsByCourse(Number(nextCourseId));
      setAssignments(items);
    } catch {
      setLoadError('Failed to load assignments.');
    } finally {
      setIsLoading(false);
    }
  }

  const filtered = useMemo(() => {
    const needle = searchQuery.trim().toLowerCase();
    if (!needle) return assignments;
    return assignments.filter((assignment) => {
      const assignmentTitle = assignment.title.toLowerCase();
      const assessmentTitle = assessmentMap.get(assignment.assessmentId)?.title?.toLowerCase() ?? '';
      const courseName =
        courses.find((course) => course.id === assignment.courseId)?.name.toLowerCase() ?? '';
      return (
        assignmentTitle.includes(needle) ||
        assessmentTitle.includes(needle) ||
        courseName.includes(needle) ||
        assignment.status.toLowerCase().includes(needle)
      );
    });
  }, [assignments, assessmentMap, courses, searchQuery]);

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Assignments</h1>
          <p className="text-muted-foreground mt-1">
            {role === 'TEACHER'
              ? 'Manage assignments you created.'
              : 'Browse assignments by course.'}
          </p>
        </div>
        {canCreate && (
          <Button onClick={() => router.push('/dashboard/assignments/new')}>
            <Plus className="mr-2 h-4 w-4" />
            Create Assignment
          </Button>
        )}
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        {role !== 'TEACHER' && (
          <div className="w-full max-w-xs">
            <Select value={selectedCourseId} onValueChange={handleCourseChange}>
              <SelectTrigger>
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
        )}

        <div className="relative flex-1 min-w-[220px] max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search assignments..."
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </div>
      </div>

      {loadError && <p className="text-sm text-destructive">{loadError}</p>}
      {isLoading && <p className="text-sm text-muted-foreground">Loading assignments...</p>}

      {!isLoading && !loadError && filtered.length === 0 && (
        <div className="rounded-sm border border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            {assignments.length === 0 ? 'No assignments found.' : 'No assignments match your search.'}
          </p>
        </div>
      )}

      {!isLoading && !loadError && filtered.length > 0 && (
        <div className="rounded-sm border border-border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted border-b border-border">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Assignment
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Template
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Course
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Status
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Opens
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Due
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((assignment) => {
                const assessmentTitle =
                  assessmentMap.get(assignment.assessmentId)?.title ??
                  `Assessment #${assignment.assessmentId}`;
                const courseName =
                  courses.find((course) => course.id === assignment.courseId)?.name ?? '-';

                return (
                  <TableRow
                    key={assignment.id}
                    className="even:bg-muted/50 hover:bg-accent transition-colors cursor-pointer"
                    onClick={() => router.push(`/dashboard/assignments/${assignment.id}`)}
                  >
                    <TableCell className="font-medium text-sm text-foreground">
                      {assignment.title}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{assessmentTitle}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{courseName}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{assignment.status}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{formatDate(assignment.openAt)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{formatDate(assignment.dueAt)}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
