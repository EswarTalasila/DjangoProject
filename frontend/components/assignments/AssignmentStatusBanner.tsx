'use client';

import { formatDate } from '@/lib/utils';

export type AssignmentStatusBannerProps = {
  viewerRole: string;
  assignmentArchived: boolean;
  assignmentNotOpen: boolean;
  openAt: string | null;
};

export default function AssignmentStatusBanner({
  viewerRole,
  assignmentArchived,
  assignmentNotOpen,
  openAt,
}: AssignmentStatusBannerProps) {
  if (viewerRole !== 'STUDENT') return null;

  if (assignmentArchived) {
    return (
      <div className="border-b border-border bg-status-error-bg px-5 py-2">
        <p className="text-sm text-foreground font-medium">
          This assignment has been archived. You can review your answers but cannot save or submit changes.
        </p>
      </div>
    );
  }

  if (assignmentNotOpen) {
    return (
      <div className="border-b border-border bg-status-warning-bg px-5 py-2">
        <p className="text-sm text-foreground font-medium">
          This assignment opens at {formatDate(openAt)}. You can preview questions but cannot save or submit until then.
        </p>
      </div>
    );
  }

  return null;
}
