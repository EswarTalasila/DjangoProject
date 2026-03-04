import { redirect } from 'next/navigation';

import ArchiveManagerView from '@/components/archive/ArchiveManagerView';
import { getSessionProfile, getSudoCapabilities } from '@/lib/auth-session';

export default async function ArchiveManagerPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (!['TEACHER', 'RESEARCHER', 'ADMIN'].includes(role)) {
    redirect('/dashboard');
  }

  const sudo = role === 'RESEARCHER' ? await getSudoCapabilities() : null;
  const canExportIdentifiable =
    role === 'RESEARCHER'
      ? sudo?.permissions?.includes('EXPORT_IDENTIFIABLE') === true
      : true;

  return (
    <ArchiveManagerView
      role={role as 'TEACHER' | 'RESEARCHER' | 'ADMIN'}
      canExportIdentifiable={canExportIdentifiable}
    />
  );
}
