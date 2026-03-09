'use client';

type CourseGradebookTabProps = { courseId: number };

export default function CourseGradebookTab({ courseId }: CourseGradebookTabProps) {
  return (
    <div className="rounded-sm border border-border bg-card p-8 text-center">
      <p className="text-sm text-muted-foreground">
        Gradebook for this course will appear here.
      </p>
    </div>
  );
}
