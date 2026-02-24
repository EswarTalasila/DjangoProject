import { redirect } from 'next/navigation';
import StudentView from '@/components/dashboard/views/StudentView';
import TeacherView from '@/components/dashboard/views/TeacherView';
import ResearcherView from '@/components/dashboard/views/ResearcherView';
import { getSessionProfile } from '@/lib/auth-session';

export default async function DashboardPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  switch (profile.role) {
    case 'TEACHER':
      return <TeacherView />;
    case 'RESEARCHER':
      return <ResearcherView />;
    case 'STUDENT':
      return <StudentView />;
    default:
      redirect('/login');
  }
}
