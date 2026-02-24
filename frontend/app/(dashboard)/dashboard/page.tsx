// app/dashboard/page.tsx
import { cookies } from 'next/headers';
import StudentView from '@/components/dashboard/views/StudentView';
import TeacherView from '@/components/dashboard/views/TeacherView';
import ResearcherView from '@/components/dashboard/views/ResearcherView';
import { notFound, redirect } from 'next/navigation';



export default async function DashboardPage() {
  // 1. Get Role from Cookies (Server-Side)
  const cookieStore = await cookies();
  // const userRole = cookieStore.get('user_role')?.value;

  const token = cookieStore.get('access_token')?.value;

  const apiUrl = process.env.BACKEND_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

  const res = await fetch(`${apiUrl}/auth/me`, {
  headers: { Authorization: `Bearer ${token}` },
  cache: 'no-store',
  });


  if (!res.ok) redirect('/login');

  const { role: userRole } = await res.json();

  console.log(userRole);

  // 2. Render the correct component
  switch (userRole) {
    case 'TEACHER':
      return <TeacherView />;
    case 'RESEARCHER':
      return <ResearcherView />;
    case 'STUDENT':
      return <StudentView />
    default:
      redirect('/login');
    
  }
}
