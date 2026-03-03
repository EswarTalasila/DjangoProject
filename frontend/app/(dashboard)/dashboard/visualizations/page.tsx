import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import VizDashboardView from '@/components/visualizations/VizDashboardView';

export default async function VisualizationsPage() {
  const profile = await getSessionProfile();
  if (!profile) redirect('/login');

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (!['TEACHER', 'RESEARCHER', 'ADMIN'].includes(role)) {
    redirect('/dashboard');
  }

  return <VizDashboardView role={role} />;
}
