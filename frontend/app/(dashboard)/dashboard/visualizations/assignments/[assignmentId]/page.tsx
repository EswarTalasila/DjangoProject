import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import VizAssignmentSummaryView from '@/components/visualizations/VizAssignmentSummaryView';

type Props = { params: Promise<{ assignmentId: string }> };

export default async function VizAssignmentPage({ params }: Props) {
  const profile = await getSessionProfile();
  if (!profile) redirect('/login');

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (!['TEACHER', 'RESEARCHER', 'ADMIN'].includes(role)) {
    redirect('/dashboard');
  }

  const { assignmentId } = await params;
  return <VizAssignmentSummaryView assignmentId={Number(assignmentId)} role={role} />;
}
