import { redirect } from 'next/navigation';
import { getSessionProfile, getSudoCapabilities } from '@/lib/auth-session';
import StaffManagementView from '@/components/staff/StaffManagementView';

export default async function Page() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  if (profile.role !== 'RESEARCHER') {
    redirect('/dashboard');
  }

  const sudo = await getSudoCapabilities();
  const permissions = sudo?.permissions ?? [];
  const isAdmin = Boolean(sudo?.isStaff);
  const canResetStudents =
    isAdmin || permissions.includes('ISSUE_STUDENT_RESET_CODE');
  const canResetResearchers =
    isAdmin || permissions.includes('ISSUE_RESEARCHER_RESET_CODE');

  return (
    <StaffManagementView
      canResetStudents={canResetStudents}
      canResetResearchers={canResetResearchers}
    />
  );
}
