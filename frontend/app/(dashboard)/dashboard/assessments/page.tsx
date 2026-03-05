import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import AssessmentListView from '@/components/assessments/AssessmentListView';

export default async function AssessmentsPage() {
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

  return <AssessmentListView canManage={canManage} />;
}
