// app/dashboard/page.tsx
import { cookies } from 'next/headers';
import StudentView from '@/components/dashboard/views/StudentView';
import TeacherView from '@/components/dashboard/views/TeacherView';
import ResearcherView from '@/components/dashboard/views/ResearcherView';
import AdminView from '@/components/dashboard/views/AdminView';

export default async function DashboardPage() {
  // 1. Get Role from Cookies (Server-Side)
  const cookieStore = await cookies();
  const userRole = cookieStore.get('user_role')?.value || 'STUDENT';
  console.log(userRole);

  // 2. Render the correct component
  switch (userRole) {
    case 'ADMIN':
        return <AdminView />
    case 'TEACHER':
      return <TeacherView />;
    case 'RESEARCHER':
      return <ResearcherView />;
    case 'STUDENT':
    default:
      return <StudentView />;
  }
}
