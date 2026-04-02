import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import AssessmentStudioShell from '@/components/assessments/studio/AssessmentStudioShell';

export default async function NewAssessmentPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.role as string;
  const canManage = role === 'RESEARCHER' || Boolean(profile.isStaff);
  if (!canManage) {
    redirect('/dashboard/assessments');
  }

  return <AssessmentStudioShell mode="create" />;
}
