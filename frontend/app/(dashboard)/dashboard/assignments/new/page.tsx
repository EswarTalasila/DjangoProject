import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import AssignmentCreateView from '@/components/assignments/AssignmentCreateView';

export default async function NewAssignmentPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (role !== 'TEACHER') {
    redirect('/dashboard/assignments');
  }

  return <AssignmentCreateView />;
}
