import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import RubricListView from '@/components/rubrics/RubricListView';

export default async function RubricsPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.role as string;
  const isAdmin = Boolean(profile.isStaff);
  if (!isAdmin && role !== 'TEACHER' && role !== 'RESEARCHER') {
    redirect('/dashboard');
  }

  const canManage = isAdmin || role === 'RESEARCHER';

  return <RubricListView canManage={canManage} />;
}
