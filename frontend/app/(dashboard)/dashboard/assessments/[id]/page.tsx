import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import AssessmentDetailView from '@/components/assessments/AssessmentDetailView';

export default async function AssessmentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.role as string;
  const isAdmin = Boolean(profile.isStaff);
  if (!isAdmin && role !== 'TEACHER' && role !== 'RESEARCHER') {
    redirect('/dashboard');
  }

  const { id } = await params;
  const assessmentId = Number(id);
  if (Number.isNaN(assessmentId)) {
    redirect('/dashboard/assessments');
  }

  const canManage = isAdmin || role === 'RESEARCHER';

  return <AssessmentDetailView assessmentId={assessmentId} canManage={canManage} />;
}
