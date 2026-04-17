import { redirect } from 'next/navigation';

import AssignmentDetailView from '@/components/assignments/AssignmentDetailView';
import { getSessionProfile } from '@/lib/auth-session';

export default async function AssignmentEditPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (role !== 'TEACHER') {
    redirect('/dashboard/assignments');
  }

  const { id } = await params;
  const assignmentId = Number(id);
  if (Number.isNaN(assignmentId)) {
    redirect('/dashboard/assignments');
  }

  return (
    <AssignmentDetailView
      assignmentId={assignmentId}
      canMutate={true}
      viewerRole="TEACHER"
      viewerId={Number(profile.id)}
      mode="edit"
    />
  );
}
