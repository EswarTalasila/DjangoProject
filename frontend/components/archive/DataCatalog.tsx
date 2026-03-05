'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Camera,
  ChevronDown,
  ChevronRight,
  Files,
  FileSpreadsheet,
  GraduationCap,
  Layers,
  Plus,
  Search,
  Users,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Input } from '@/components/ui/input';
import { StatusBadge } from '@/components/ui/status-badge';
import { listAssessments, type Assessment } from '@/lib/assessment-api';
import { listCourses, type CourseSummary } from '@/lib/course-api';
import {
  createSnapshot,
  listSnapshots,
  type DataSnapshot,
  type DatasetBinding,
  type NodeSourceType,
} from '@/lib/package-api';
import { listRubrics, type Rubric } from '@/lib/rubric-api';
import { toErrorMessage } from '@/lib/utils';

type DataCatalogProps = {
  workspaceId: number;
  canExportIdentifiable: boolean;
  onAddItem: (config: {
    label: string;
    datasetBinding: DatasetBinding;
    bindingCourseId: number | null;
    sourceType?: NodeSourceType;
    snapshotId?: number | null;
  }) => void;
};

export default function DataCatalog({
  workspaceId,
  canExportIdentifiable,
  onAddItem,
}: DataCatalogProps) {
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [snapshots, setSnapshots] = useState<DataSnapshot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingSnapshot, setIsCreatingSnapshot] = useState(false);
  const [filterText, setFilterText] = useState('');

  /* Collapsible section state */
  const [globalOpen, setGlobalOpen] = useState(true);
  const [coursesOpen, setCoursesOpen] = useState(true);
  const [snapshotsOpen, setSnapshotsOpen] = useState(true);
  const [assessmentsOpen, setAssessmentsOpen] = useState(true);
  const [rubricsOpen, setRubricsOpen] = useState(true);
  /* Per-course expansion within the courses section */
  const [expandedCourses, setExpandedCourses] = useState<Set<number>>(
    new Set(),
  );

  useEffect(() => {
    void loadCatalog();
  }, []);

  async function loadCatalog() {
    setIsLoading(true);
    try {
      const [courseList, assessmentList, rubricList] = await Promise.all([
        listCourses({ includeArchived: true }),
        listAssessments(),
        listRubrics(),
      ]);
      const snapshotList = await listSnapshots(workspaceId);
      setCourses(courseList);
      setAssessments(assessmentList);
      setRubrics(rubricList);
      setSnapshots(snapshotList);
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }

  const lowerFilter = filterText.toLowerCase();

  const filteredCourses = useMemo(
    () =>
      courses.filter((course) =>
        course.name.toLowerCase().includes(lowerFilter),
      ),
    [courses, lowerFilter],
  );

  const filteredAssessments = useMemo(
    () =>
      assessments.filter((assessment) =>
        assessment.title.toLowerCase().includes(lowerFilter),
      ),
    [assessments, lowerFilter],
  );

  const filteredRubrics = useMemo(
    () =>
      rubrics.filter((rubric) =>
        rubric.title.toLowerCase().includes(lowerFilter),
      ),
    [rubrics, lowerFilter],
  );

  const filteredSnapshots = useMemo(() => {
    return snapshots.filter((snapshot) => {
      const name = String(
        snapshot.metadata?.courseName ?? snapshot.datasetBinding,
      ).toLowerCase();
      return name.includes(lowerFilter);
    });
  }, [snapshots, lowerFilter]);

  const showCrossCourse =
    lowerFilter.length === 0 ||
    'cross-course submissions'.includes(lowerFilter) ||
    'cross course submissions'.includes(lowerFilter) ||
    'global data'.includes(lowerFilter);

  function bindingLabel(binding: DatasetBinding) {
    if (binding === 'ROSTER') return 'Roster';
    if (binding === 'COURSE_SUBMISSIONS') return 'Course Submissions';
    return 'Cross-Course Submissions';
  }

  function snapshotDisplayName(snapshot: DataSnapshot) {
    const courseName = snapshot.metadata?.courseName;
    if (typeof courseName === 'string' && courseName.trim()) {
      return `${courseName} — ${bindingLabel(snapshot.datasetBinding)}`;
    }
    return bindingLabel(snapshot.datasetBinding);
  }

  function toggleCourse(courseId: number) {
    setExpandedCourses((prev) => {
      const next = new Set(prev);
      if (next.has(courseId)) {
        next.delete(courseId);
      } else {
        next.add(courseId);
      }
      return next;
    });
  }

  async function handleTakeSnapshot(config: {
    datasetBinding: DatasetBinding;
    scopeCourseId: number | null;
    label: string;
    includeAnswers?: boolean;
  }) {
    setIsCreatingSnapshot(true);
    try {
      const snapshot = await createSnapshot(workspaceId, {
        datasetBinding: config.datasetBinding,
        scopeCourseId: config.scopeCourseId,
        includeAnswers: config.includeAnswers ?? false,
        identifiable: canExportIdentifiable ? undefined : false,
      });
      setSnapshots((prev) => [snapshot, ...prev]);
      toast.success(`${config.label} snapshot created.`);
    } catch (error) {
      toast.error(toErrorMessage(error));
    } finally {
      setIsCreatingSnapshot(false);
    }
  }

  function addSnapshotToPackage(snapshot: DataSnapshot) {
    const baseName =
      (snapshot.metadata?.courseName as string | undefined) ??
      snapshot.datasetBinding.replaceAll('_', ' ');
    onAddItem({
      label: `${baseName} — Snapshot.csv`,
      datasetBinding: snapshot.datasetBinding,
      bindingCourseId: snapshot.scopeCourseId,
      sourceType: 'SNAPSHOT',
      snapshotId: snapshot.id,
    });
  }

  if (isLoading) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Loading catalog...
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Filter input */}
      <div className="relative">
        <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
        <Input
          value={filterText}
          onChange={(event) => setFilterText(event.target.value)}
          placeholder="Filter by name..."
          className="pl-9"
        />
      </div>
      <p className="px-1 text-xs text-muted-foreground">
        Camera icons create snapshots. Plus icons add either live or snapshot
        data directly into the explorer.
      </p>

      {/* Courses section */}
      <Collapsible open={globalOpen} onOpenChange={setGlobalOpen}>
        <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm font-semibold text-foreground hover:bg-accent/30">
          {globalOpen ? (
            <ChevronDown className="size-4" />
          ) : (
            <ChevronRight className="size-4" />
          )}
          <Files className="size-4" />
          Global Data
          <span className="ml-auto text-xs text-muted-foreground">
            {showCrossCourse ? 1 : 0}
          </span>
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-0.5 pl-2">
          {showCrossCourse ? (
            <>
              <div className="flex items-center gap-2 rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-accent/30">
                <FileSpreadsheet className="size-3.5 text-purple-500" />
                <span className="truncate">Cross-Course Submissions</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="ml-auto h-6 w-6 p-0"
                  title="Take snapshot of cross-course submissions"
                  disabled={isCreatingSnapshot}
                  onClick={() =>
                    void handleTakeSnapshot({
                      datasetBinding: 'CROSS_COURSE_SUBMISSIONS',
                      scopeCourseId: null,
                      label: 'Cross-course submissions',
                      includeAnswers: false,
                    })
                  }
                >
                  <Camera className="size-3.5" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                  title="Add Cross-Course Submissions to package"
                  onClick={() =>
                    onAddItem({
                      label: 'Cross-Course Submissions.csv',
                      datasetBinding: 'CROSS_COURSE_SUBMISSIONS',
                      bindingCourseId: null,
                    })
                  }
                >
                  <Plus className="size-3.5" />
                </Button>
              </div>
              <p className="px-2 pb-0.5 text-xs text-muted-foreground">
                Snapshot available here. No need to use Quick Export first.
              </p>
            </>
          ) : (
            <p className="px-2 py-1 text-xs text-muted-foreground">
              No global datasets found.
            </p>
          )}
        </CollapsibleContent>
      </Collapsible>

      {/* Courses section */}
      <Collapsible open={coursesOpen} onOpenChange={setCoursesOpen}>
        <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm font-semibold text-foreground hover:bg-accent/30">
          {coursesOpen ? (
            <ChevronDown className="size-4" />
          ) : (
            <ChevronRight className="size-4" />
          )}
          <GraduationCap className="size-4" />
          Courses
          <span className="ml-auto text-xs text-muted-foreground">
            {filteredCourses.length}
          </span>
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-0.5 pl-2">
          {filteredCourses.length === 0 ? (
            <p className="px-2 py-1 text-xs text-muted-foreground">
              No courses found.
            </p>
          ) : (
            filteredCourses.map((course) => {
              const isExpanded = expandedCourses.has(course.id);
              return (
                <div key={course.id}>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground hover:bg-accent/30"
                    onClick={() => toggleCourse(course.id)}
                  >
                    {isExpanded ? (
                      <ChevronDown className="size-3.5" />
                    ) : (
                      <ChevronRight className="size-3.5" />
                    )}
                    <span className="truncate font-medium text-foreground">
                      {course.name}
                    </span>
                    <StatusBadge
                      status={course.status}
                      className="ml-auto shrink-0"
                    />
                  </button>
                  {course.status === 'ACTIVE' ? (
                    <p className="px-2 pb-0.5 text-xs text-muted-foreground">
                      Snapshot taken on build
                    </p>
                  ) : course.status === 'ARCHIVED' ? (
                    <p className="px-2 pb-0.5 text-xs text-muted-foreground">
                      Static — export ready
                    </p>
                  ) : null}
                  {isExpanded && (
                    <div className="space-y-0.5 pl-6">
                      {/* Roster sub-item */}
                      <div className="flex items-center gap-2 rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-accent/30">
                        <Users className="size-3.5 text-green-500" />
                        <span className="truncate">Roster</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="ml-auto h-6 w-6 p-0"
                          title="Take snapshot of roster"
                          disabled={isCreatingSnapshot}
                          onClick={() =>
                            void handleTakeSnapshot({
                              datasetBinding: 'ROSTER',
                              scopeCourseId: course.id,
                              label: `${course.name} roster`,
                            })
                          }
                        >
                          <Camera className="size-3.5" />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          title="Add Roster to package"
                          onClick={() =>
                            onAddItem({
                              label: `${course.name} — Roster.csv`,
                              datasetBinding: 'ROSTER',
                              bindingCourseId: course.id,
                            })
                          }
                        >
                          <Plus className="size-3.5" />
                        </Button>
                      </div>
                      {/* Submissions sub-item */}
                      <div className="flex items-center gap-2 rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-accent/30">
                        <FileSpreadsheet className="size-3.5 text-purple-500" />
                        <span className="truncate">Submissions</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="ml-auto h-6 w-6 p-0"
                          title="Take snapshot of submissions"
                          disabled={isCreatingSnapshot}
                          onClick={() =>
                            void handleTakeSnapshot({
                              datasetBinding: 'COURSE_SUBMISSIONS',
                              scopeCourseId: course.id,
                              label: `${course.name} submissions`,
                              includeAnswers: false,
                            })
                          }
                        >
                          <Camera className="size-3.5" />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          title="Add Submissions to package"
                          onClick={() =>
                            onAddItem({
                              label: `${course.name} — Submissions.csv`,
                              datasetBinding: 'COURSE_SUBMISSIONS',
                              bindingCourseId: course.id,
                            })
                          }
                        >
                          <Plus className="size-3.5" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </CollapsibleContent>
      </Collapsible>

      {/* Snapshots section */}
      <Collapsible open={snapshotsOpen} onOpenChange={setSnapshotsOpen}>
        <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm font-semibold text-foreground hover:bg-accent/30">
          {snapshotsOpen ? (
            <ChevronDown className="size-4" />
          ) : (
            <ChevronRight className="size-4" />
          )}
          <Camera className="size-4" />
          Snapshots
          <span className="ml-auto text-xs text-muted-foreground">
            {filteredSnapshots.length}
          </span>
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-0.5 pl-2">
          {filteredSnapshots.length === 0 ? (
            <p className="px-2 py-1 text-xs text-muted-foreground">
              No snapshots yet. Use the camera buttons in Courses to create one.
            </p>
          ) : (
            filteredSnapshots.map((snapshot) => {
              const capturedAt =
                typeof snapshot.metadata?.capturedAt === 'string'
                  ? snapshot.metadata.capturedAt
                  : snapshot.createdAt;
              return (
                <div key={snapshot.id} className="rounded-md px-2 py-1.5">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <FileSpreadsheet className="size-3.5 shrink-0 text-amber-600" />
                    <span className="truncate font-medium text-foreground">
                      {snapshotDisplayName(snapshot)}
                    </span>
                    <StatusBadge status={snapshot.status} className="shrink-0" />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="ml-auto h-6 w-6 p-0"
                      title="Add snapshot to package"
                      onClick={() => addSnapshotToPackage(snapshot)}
                      disabled={snapshot.status !== 'READY'}
                    >
                      <Plus className="size-3.5" />
                    </Button>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Captured {new Date(capturedAt).toLocaleString()} · {snapshot.rowCount}{' '}
                    rows
                  </p>
                </div>
              );
            })
          )}
        </CollapsibleContent>
      </Collapsible>

      {/* Assessments section */}
      <Collapsible open={assessmentsOpen} onOpenChange={setAssessmentsOpen}>
        <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm font-semibold text-foreground hover:bg-accent/30">
          {assessmentsOpen ? (
            <ChevronDown className="size-4" />
          ) : (
            <ChevronRight className="size-4" />
          )}
          <Layers className="size-4" />
          Assessments
          <span className="ml-auto text-xs text-muted-foreground">
            {filteredAssessments.length}
          </span>
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-0.5 pl-2">
          {filteredAssessments.length === 0 ? (
            <p className="px-2 py-1 text-xs text-muted-foreground">
              No assessments found.
            </p>
          ) : (
            filteredAssessments.map((assessment) => (
              <div key={assessment.id} className="rounded-md px-2 py-1.5">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Layers className="size-3.5 shrink-0" />
                  <span className="truncate font-medium text-foreground">
                    {assessment.title}
                  </span>
                  {assessment.status && (
                    <StatusBadge
                      status={assessment.status}
                      className="shrink-0"
                    />
                  )}
                  <span className="ml-auto text-xs text-muted-foreground italic whitespace-nowrap">
                    Template export coming soon
                  </span>
                </div>
              </div>
            ))
          )}
        </CollapsibleContent>
      </Collapsible>

      {/* Rubrics section */}
      <Collapsible open={rubricsOpen} onOpenChange={setRubricsOpen}>
        <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm font-semibold text-foreground hover:bg-accent/30">
          {rubricsOpen ? (
            <ChevronDown className="size-4" />
          ) : (
            <ChevronRight className="size-4" />
          )}
          <Layers className="size-4" />
          Rubrics
          <span className="ml-auto text-xs text-muted-foreground">
            {filteredRubrics.length}
          </span>
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-0.5 pl-2">
          {filteredRubrics.length === 0 ? (
            <p className="px-2 py-1 text-xs text-muted-foreground">
              No rubrics found.
            </p>
          ) : (
            filteredRubrics.map((rubric) => (
              <div key={rubric.id} className="rounded-md px-2 py-1.5">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Layers className="size-3.5 shrink-0" />
                  <span className="truncate font-medium text-foreground">
                    {rubric.title}
                  </span>
                  <StatusBadge
                    status={rubric.status}
                    className="shrink-0"
                  />
                  <span className="ml-auto text-xs text-muted-foreground italic whitespace-nowrap">
                    Template export coming soon
                  </span>
                </div>
              </div>
            ))
          )}
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
