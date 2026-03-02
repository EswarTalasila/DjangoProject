'use client';

type CourseAssignmentsTabProps = { courseId: number };

export default function CourseAssignmentsTab({ courseId }: CourseAssignmentsTabProps) {
  return (
    <div className="rounded-sm border border-border bg-card p-8 text-center">
      <p className="text-sm text-muted-foreground">
        Assignments for this course will appear here.
      </p>
    </div>
  );
}
