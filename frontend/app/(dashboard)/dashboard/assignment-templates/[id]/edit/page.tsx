import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import AssignmentTemplateStudioShell from '@/components/assignment-templates/studio/AssignmentTemplateStudioShell';

export default async function EditAssignmentTemplatePage({
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
    redirect('/dashboard/assignment-templates');
  }

  const { id } = await params;
  const assignmentTemplateId = Number(id);
  if (Number.isNaN(assignmentTemplateId)) {
    redirect('/dashboard/assignment-templates');
  }

  return <AssignmentTemplateStudioShell mode="edit" assignmentTemplateId={assignmentTemplateId} />;
}
