import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
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

  return <CodeManagementView userRole={role as 'TEACHER' | 'RESEARCHER'} />;
}
