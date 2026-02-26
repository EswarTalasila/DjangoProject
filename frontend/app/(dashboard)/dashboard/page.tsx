// app/dashboard/page.tsx
import StudentView from '@/components/dashboard/views/StudentView';
import TeacherView from '@/components/dashboard/views/TeacherView';
import ResearcherView from '@/components/dashboard/views/ResearcherView';
import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';

export default async function DashboardPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  // 2. Render the correct component
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
