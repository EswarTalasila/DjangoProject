import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import RubricDetailView from '@/components/rubrics/RubricDetailView';

export default async function RubricDetailPage({
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
  const rubricId = Number(id);
  if (Number.isNaN(rubricId)) {
    redirect('/dashboard/rubrics');
  }

  const canManage = isAdmin || role === 'RESEARCHER';

  return <RubricDetailView rubricId={rubricId} canManage={canManage} />;
}
