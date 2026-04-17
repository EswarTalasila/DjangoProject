import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import AssignmentDetailView from '@/components/assignments/AssignmentDetailView';

export default async function AssignmentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (role !== 'TEACHER' && role !== 'ADMIN' && role !== 'STUDENT') {
    redirect('/dashboard');
  }

  const { id } = await params;
  const assignmentId = Number(id);
  if (Number.isNaN(assignmentId)) {
    redirect('/dashboard/assignments');
  }

  const canMutate = role === 'TEACHER';

  return (
    <AssignmentDetailView
      assignmentId={assignmentId}
      canMutate={canMutate}
      viewerRole={role as 'TEACHER' | 'ADMIN' | 'STUDENT'}
      viewerId={Number(profile.id)}
    />
  );
}
