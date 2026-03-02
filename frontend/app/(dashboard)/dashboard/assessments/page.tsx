import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import AssessmentListView from '@/components/assessments/AssessmentListView';

export default async function AssessmentsPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.role as string;
  if (role !== 'TEACHER' && role !== 'RESEARCHER') {
    redirect('/dashboard');
  }

  const canManage = role === 'RESEARCHER' || Boolean(profile.isStaff);

  return <AssessmentListView canManage={canManage} />;
}
