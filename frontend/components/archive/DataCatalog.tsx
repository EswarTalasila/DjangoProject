'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
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
import type { DatasetBinding } from '@/lib/package-api';
import { listRubrics, type Rubric } from '@/lib/rubric-api';
import { toErrorMessage } from '@/lib/utils';

type DataCatalogProps = {
  onAddItem: (config: {
    label: string;
    datasetBinding: DatasetBinding;
    bindingCourseId: number | null;
  }) => void;
};

export default function DataCatalog({ onAddItem }: DataCatalogProps) {
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterText, setFilterText] = useState('');

  /* Collapsible section state */
  const [coursesOpen, setCoursesOpen] = useState(true);
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
      setCourses(courseList);
      setAssessments(assessmentList);
      setRubrics(rubricList);
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
                    Not yet exportable
                  </span>
                </div>
                {assessment.status === 'ACTIVE' ? (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Snapshot taken on build
                  </p>
                ) : assessment.status === 'ARCHIVED' ? (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Static — export ready
                  </p>
                ) : null}
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
                    Not yet exportable
                  </span>
                </div>
                {rubric.status === 'ACTIVE' ? (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Snapshot taken on build
                  </p>
                ) : rubric.status === 'ARCHIVED' ? (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Static — export ready
                  </p>
                ) : null}
              </div>
            ))
          )}
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
