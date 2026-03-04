import { redirect } from 'next/navigation';

import SubmissionsHubView from '@/components/submissions/SubmissionsHubView';
import { getSessionProfile } from '@/lib/auth-session';

export default async function SubmissionsPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (role !== 'TEACHER' && role !== 'RESEARCHER' && role !== 'ADMIN' && role !== 'STUDENT') {
    redirect('/dashboard');
  }

  return (
    <SubmissionsHubView
      role={role as 'TEACHER' | 'RESEARCHER' | 'ADMIN' | 'STUDENT'}
      userId={Number(profile.id)}
    />
  );
}
