'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Check, Pencil, X } from 'lucide-react';
import { toast } from 'sonner';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
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
import {
  addStudentToCourse,
  getCourse,
  listStudentsInCourse,
  removeStudentFromCourse,
  updateCourse,
  type CourseSummary,
  type CourseStudent,
} from '@/lib/course-api';

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

type CourseDetailViewProps = {
  courseId: number;
  userRole: 'TEACHER' | 'RESEARCHER';
  userId: number;
};

export default function CourseDetailView({
  courseId,
  userRole,
}: CourseDetailViewProps) {
  const canManage = userRole === 'TEACHER';

  // Course data
  const [course, setCourse] = useState<CourseSummary | null>(null);
  const [students, setStudents] = useState<CourseStudent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Inline name editing
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState('');
  const [isSavingName, setIsSavingName] = useState(false);

  // Add student form
  const [newStudentName, setNewStudentName] = useState('');
  const [newStudentConsent, setNewStudentConsent] = useState(false);
  const [isAddingStudent, setIsAddingStudent] = useState(false);

  // Remove student
  const [removingStudentId, setRemovingStudentId] = useState<number | null>(
    null
  );

  const loadCourse = useCallback(async () => {
    setLoadError(null);
    try {
      const [courseData, studentData] = await Promise.all([
        getCourse(courseId),
        listStudentsInCourse(courseId),
      ]);
      setCourse(courseData);
      setStudents(studentData);
    } catch {
      setLoadError('Failed to load course details.');
    } finally {
      setIsLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    setIsLoading(true);
    void loadCourse();
  }, [loadCourse]);

  // -- Name editing --
  function startEditingName() {
    if (!course) return;
    setEditedName(course.name);
    setIsEditingName(true);
  }

  function cancelEditingName() {
    setIsEditingName(false);
    setEditedName('');
  }

  async function saveName() {
    const trimmed = editedName.trim();
    if (!trimmed || !course) return;

    setIsSavingName(true);
    try {
      const updated = await updateCourse(courseId, trimmed);
      setCourse(updated);
      setIsEditingName(false);
      toast.success('Course name updated.');
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to update course name.'));
    } finally {
      setIsSavingName(false);
    }
  }

  // -- Add student --
  async function handleAddStudent() {
    const trimmed = newStudentName.trim();
    if (!trimmed) return;

    setIsAddingStudent(true);
    try {
      await addStudentToCourse(courseId, {
        name: trimmed,
        consent: newStudentConsent,
      });
      toast.success(`Student "${trimmed}" added.`);
      setNewStudentName('');
      setNewStudentConsent(false);
      await loadCourse();
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to add student.'));
    } finally {
      setIsAddingStudent(false);
    }
  }

  // -- Remove student --
  async function handleRemoveStudent(studentId: number, studentName: string) {
    setRemovingStudentId(studentId);
    try {
      await removeStudentFromCourse(courseId, studentId);
      toast.success(`Student "${studentName}" removed.`);
      await loadCourse();
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to remove student.'));
    } finally {
      setRemovingStudentId(null);
    }
  }

  // -- Loading / Error states --
  if (isLoading) {
    return (
      <div className="space-y-6 p-6 max-w-6xl mx-auto">
        <p className="text-sm text-muted-foreground">Loading course...</p>
      </div>
    );
  }

  if (loadError || !course) {
    return (
      <div className="space-y-6 p-6 max-w-6xl mx-auto">
        <Link
          href="/dashboard/courses"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Courses
        </Link>
        <p className="text-sm text-destructive">
          {loadError || 'Course not found.'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      {/* Back link */}
      <Link
        href="/dashboard/courses"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Courses
      </Link>

      {/* Header */}
      <div className="space-y-1">
        {isEditingName ? (
          <div className="flex items-center gap-2">
            <Input
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !isSavingName) void saveName();
                if (e.key === 'Escape') cancelEditingName();
              }}
              disabled={isSavingName}
              className="text-2xl font-bold h-auto py-1 max-w-md"
              autoFocus
            />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => void saveName()}
              disabled={isSavingName || !editedName.trim()}
              aria-label="Save name"
            >
              <Check className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={cancelEditingName}
              disabled={isSavingName}
              aria-label="Cancel editing"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight text-foreground">
              {course.name}
            </h1>
            {canManage && (
              <Button
                variant="ghost"
                size="icon"
                onClick={startEditingName}
                aria-label="Edit course name"
              >
                <Pencil className="h-4 w-4" />
              </Button>
            )}
          </div>
        )}
        <p className="text-sm text-muted-foreground">
          {course.teacherName ? `Teacher: ${course.teacherName}` : ''}
          {course.teacherName && course.createdAt ? ' \u00b7 ' : ''}
          {course.createdAt ? `Created ${formatDate(course.createdAt)}` : ''}
        </p>
      </div>

      {/* Add Student (TEACHER only) */}
      {canManage && (
        <div className="rounded-sm border border-border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground mb-3">
            Add Student
          </h2>
          <div className="flex items-end gap-3 flex-wrap">
            <div className="space-y-1 flex-1 min-w-[200px] max-w-sm">
              <Label htmlFor="student-name" className="text-xs text-muted-foreground">
                Student Name
              </Label>
              <Input
                id="student-name"
                placeholder="e.g. Jane Doe"
                value={newStudentName}
                onChange={(e) => setNewStudentName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !isAddingStudent)
                    void handleAddStudent();
                }}
                disabled={isAddingStudent}
              />
            </div>
            <div className="flex items-center gap-2 pb-1">
              <Checkbox
                id="student-consent"
                checked={newStudentConsent}
                onCheckedChange={(checked) =>
                  setNewStudentConsent(checked === true)
                }
                disabled={isAddingStudent}
              />
              <Label
                htmlFor="student-consent"
                className="text-sm text-muted-foreground cursor-pointer"
              >
                Parental consent
              </Label>
            </div>
            <Button
              onClick={() => void handleAddStudent()}
              disabled={isAddingStudent || !newStudentName.trim()}
              className="shrink-0"
            >
              {isAddingStudent ? 'Adding...' : 'Add'}
            </Button>
          </div>
        </div>
      )}

      {/* Students table */}
      <div>
        <h2 className="text-lg font-semibold text-foreground mb-3">
          Students ({students.length})
        </h2>
        {students.length === 0 ? (
          <div className="rounded-sm border border-border bg-card p-8 text-center">
            <p className="text-sm text-muted-foreground">
              {canManage
                ? 'No students enrolled yet. Add a student above to get started.'
                : 'No students enrolled in this course.'}
            </p>
          </div>
        ) : (
          <div className="rounded-sm border border-border bg-card overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted border-b border-border">
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Name
                  </TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Username
                  </TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Enrolled
                  </TableHead>
                  {canManage && (
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground w-24">
                      Actions
                    </TableHead>
                  )}
                </TableRow>
              </TableHeader>
              <TableBody>
                {students.map((student) => (
                  <TableRow
                    key={student.id}
                    className="even:bg-muted/50 hover:bg-accent transition-colors"
                  >
                    <TableCell className="font-medium text-sm text-foreground">
                      {student.name}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {student.username}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(student.enrolledAt)}
                    </TableCell>
                    {canManage && (
                      <TableCell>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive"
                              disabled={removingStudentId === student.id}
                            >
                              {removingStudentId === student.id
                                ? 'Removing...'
                                : 'Remove'}
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>
                                Remove Student
                              </AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to remove{' '}
                                <span className="font-medium">
                                  {student.name}
                                </span>{' '}
                                from this course? This action cannot be undone.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() =>
                                  void handleRemoveStudent(
                                    student.id,
                                    student.name
                                  )
                                }
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              >
                                Remove
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Delete course button (TEACHER only, disabled) */}
      {canManage && (
        <div className="border-t border-border pt-6">
          <h2 className="text-sm font-semibold text-foreground mb-2">
            Danger Zone
          </h2>
          <Button
            variant="destructive"
            disabled
            title="Requires archival — not yet available"
          >
            Delete Course
          </Button>
          <p className="text-xs text-muted-foreground mt-1">
            Requires archival — not yet available
          </p>
        </div>
      )}
    </div>
  );
}
