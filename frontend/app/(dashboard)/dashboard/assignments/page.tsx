import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import AssignmentListView from '@/components/assignments/AssignmentListView';

export default async function AssignmentsPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (role !== 'TEACHER' && role !== 'RESEARCHER' && role !== 'ADMIN') {
    redirect('/dashboard');
  }

  const canCreate = role === 'TEACHER';

  return <AssignmentListView role={role as 'TEACHER' | 'RESEARCHER' | 'ADMIN'} userId={profile.id} canCreate={canCreate} />;
}
