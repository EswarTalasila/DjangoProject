import { redirect } from 'next/navigation';

import { getSessionProfile, getSudoCapabilities } from '@/lib/auth-session';
import PackageWorkspaceConsole from '@/components/packages/PackageWorkspaceConsole';

export default async function PackagesPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (!['TEACHER', 'ADMIN'].includes(role)) {
    if (role !== 'RESEARCHER') {
      redirect('/dashboard');
    }
    const sudo = await getSudoCapabilities();
    const canExport = sudo?.permissions?.includes('EXPORT_IDENTIFIABLE') === true;
    if (!canExport) {
      redirect('/dashboard');
    }
  }

  return <PackageWorkspaceConsole role={role as 'TEACHER' | 'RESEARCHER' | 'ADMIN'} />;
}
