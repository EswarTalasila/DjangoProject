import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import AssignmentTemplateDetailView from '@/components/assignment-templates/AssignmentTemplateDetailView';

export default async function AssignmentTemplateDetailPage({
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
  const assignmentTemplateId = Number(id);
  if (Number.isNaN(assignmentTemplateId)) {
    redirect('/dashboard/assignment-templates');
  }

  const canManage = isAdmin || role === 'RESEARCHER';

  return <AssignmentTemplateDetailView assignmentTemplateId={assignmentTemplateId} canManage={canManage} />;
}
