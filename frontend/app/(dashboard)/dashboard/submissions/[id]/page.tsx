import { redirect } from 'next/navigation';

import SubmissionDetailView from '@/components/submissions/SubmissionDetailView';
import { getSessionProfile, getSudoCapabilities } from '@/lib/auth-session';

export default async function SubmissionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (role !== 'TEACHER' && role !== 'RESEARCHER' && role !== 'ADMIN' && role !== 'STUDENT') {
    redirect('/dashboard');
  }
  if (role === 'RESEARCHER') {
    const sudo = await getSudoCapabilities();
    const canViewSubmissions = sudo?.permissions?.includes('VIEW_SUBMISSIONS') === true;
    if (!canViewSubmissions) {
      redirect('/dashboard');
    }
  }

  const { id } = await params;
  const submissionId = Number(id);
  if (Number.isNaN(submissionId)) {
    redirect('/dashboard/submissions');
  }

  return (
    <SubmissionDetailView
      submissionId={submissionId}
      viewerRole={role as 'TEACHER' | 'RESEARCHER' | 'ADMIN' | 'STUDENT'}
    />
  );
}
