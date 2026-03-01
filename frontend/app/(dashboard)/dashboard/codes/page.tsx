import { redirect } from 'next/navigation';
import { getSessionProfile, getSudoCapabilities } from '@/lib/auth-session';
import CodeManagementView from '@/components/codes/CodeManagementView';

export default async function CodesPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.role as string;
  if (role !== 'TEACHER' && role !== 'RESEARCHER') {
    redirect('/dashboard');
  }

  let researcherPermissions: string[] = [];
  let isStaff = Boolean(profile.isStaff);
  if (role === 'RESEARCHER') {
    const sudo = await getSudoCapabilities();
    researcherPermissions = sudo?.permissions ?? [];
    isStaff = isStaff || Boolean(sudo?.isStaff);
  }

  return (
    <CodeManagementView
      userRole={role as 'TEACHER' | 'RESEARCHER'}
      researcherPermissions={researcherPermissions}
      isStaff={isStaff}
    />
  );
}
