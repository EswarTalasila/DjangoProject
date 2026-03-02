import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import StaffManagementView from '@/components/staff/StaffManagementView';

export default async function StaffPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  if (profile.role !== 'RESEARCHER') {
    redirect('/dashboard');
  }

  return <StaffManagementView />;
}
