import { redirect } from 'next/navigation';

import ExportsHubView from '@/components/exports/ExportsHubView';
import { getSessionProfile } from '@/lib/auth-session';

export default async function ExportsPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (!['TEACHER', 'RESEARCHER', 'ADMIN'].includes(role)) {
    redirect('/dashboard');
  }

  return <ExportsHubView role={role as 'TEACHER' | 'RESEARCHER' | 'ADMIN'} />;
}
