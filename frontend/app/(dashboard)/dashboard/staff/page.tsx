import { redirect } from 'next/navigation';
import { getSessionProfile, getSudoCapabilities } from '@/lib/auth-session';
import StaffManagementView from '@/components/staff/StaffManagementView';

export default async function StaffPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  if (profile.role !== 'RESEARCHER') {
    redirect('/dashboard');
  }

  const sudo = await getSudoCapabilities();
  const permissions = sudo?.permissions ?? [];
  const canResetStudents =
    Boolean(sudo?.isStaff) ||
    permissions.includes('ISSUE_STUDENT_RESET_CODE');

  return <StaffManagementView canResetStudents={canResetStudents} />;
}
