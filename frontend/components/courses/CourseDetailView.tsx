'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { ArrowLeft, Check, Pencil, X } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { getCourse, updateCourse, type CourseSummary } from '@/lib/course-api';
import CourseRosterTab from './CourseRosterTab';
import CourseRegistrationTab from './CourseRegistrationTab';
import CourseAssignmentsTab from './CourseAssignmentsTab';
import CourseGradebookTab from './CourseGradebookTab';
import { toErrorMessage } from '@/lib/utils';

const TABS = ['roster', 'registration', 'assignments', 'gradebook'] as const;
type Tab = (typeof TABS)[number];

const TAB_LABELS: Record<Tab, string> = {
  roster: 'Roster',
  registration: 'Registration',
  assignments: 'Assignments',
  gradebook: 'Gradebook',
};

type CourseDetailViewProps = {
  courseId: number;
  userRole: 'TEACHER' | 'RESEARCHER' | 'STUDENT';
  userId: number;
};

export default function CourseDetailView({
  courseId,
  userRole,
  userId,
}: CourseDetailViewProps) {
  const canManage = userRole === 'TEACHER';

  // Teachers see all tabs, students see assignments only, researchers see roster only
  const visibleTabs: Tab[] = canManage
    ? [...TABS]
    : userRole === 'STUDENT'
      ? ['assignments']
      : ['roster'];

  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const rawTab = searchParams.get('tab');
  const activeTab: Tab =
    rawTab && visibleTabs.includes(rawTab as Tab) ? (rawTab as Tab) : visibleTabs[0];

  function setTab(tab: Tab) {
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', tab);
    router.replace(`${pathname}?${params.toString()}`);
  }

  // Course header data
  const [course, setCourse] = useState<CourseSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Inline name editing
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState('');
  const [isSavingName, setIsSavingName] = useState(false);

  const loadCourse = useCallback(async () => {
    setLoadError(null);
    try {
      const courseData = await getCourse(courseId);
      setCourse(courseData);
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
      toast.error(toErrorMessage(error, 'Failed to update course name.'));
    } finally {
      setIsSavingName(false);
    }
  }

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
          {course.createdAt
            ? `Created ${new Date(course.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`
            : ''}
        </p>
      </div>

      {/* Tab bar */}
      <div className="border-b border-border">
        <nav className="flex gap-4" aria-label="Course tabs">
          {visibleTabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setTab(tab)}
              className={`pb-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === tab
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content (lazy-loaded) */}
      {activeTab === 'roster' && (
        <CourseRosterTab courseId={courseId} canManage={canManage} />
      )}
      {activeTab === 'registration' && canManage && (
        <CourseRegistrationTab courseId={courseId} />
      )}
      {activeTab === 'assignments' && (
        <CourseAssignmentsTab
          courseId={courseId}
          userRole={userRole}
          userId={userId}
        />
      )}
      {activeTab === 'gradebook' && canManage && (
        <CourseGradebookTab courseId={courseId} />
      )}
    </div>
  );
}
