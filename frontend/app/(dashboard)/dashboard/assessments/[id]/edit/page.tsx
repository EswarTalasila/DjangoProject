import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import AssessmentStudioShell from '@/components/assessments/studio/AssessmentStudioShell';

export default async function EditAssessmentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.role as string;
  const canManage = role === 'RESEARCHER' || Boolean(profile.isStaff);
  if (!canManage) {
    redirect('/dashboard/assessments');
  }

  const { id } = await params;
  const assessmentId = Number(id);
  if (Number.isNaN(assessmentId)) {
    redirect('/dashboard/assessments');
  }

  return <AssessmentStudioShell mode="edit" assessmentId={assessmentId} />;
}
