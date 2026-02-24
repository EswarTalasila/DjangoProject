import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import StudentView from '@/components/dashboard/views/StudentView';
import TeacherView from '@/components/dashboard/views/TeacherView';
import ResearcherView from '@/components/dashboard/views/ResearcherView';

type SessionProfile = {
  role?: string;
};

function resolveApiBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  try {
    const url = new URL(configured);
    if ((url.hostname === 'localhost' || url.hostname === '127.0.0.1') && process.env.PROXY_TARGET) {
      const proxyTarget = process.env.PROXY_TARGET.replace(/\/$/, '');
      return `${proxyTarget}/api/v1`;
    }
    return url.toString().replace(/\/$/, '');
  } catch {
    return configured.replace(/\/$/, '');
  }
}

export default async function DashboardPage() {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get('access_token')?.value;
  if (!accessToken) {
    redirect('/login');
  }

  let response: Response;
  try {
    response = await fetch(`${resolveApiBaseUrl()}/auth/me`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      cache: 'no-store',
    });
  } catch {
    redirect('/login');
  }

  if (!response.ok) {
    redirect('/login');
  }

  const profile = (await response.json()) as SessionProfile;
  const userRole = profile.role;
  if (!userRole || !['TEACHER', 'RESEARCHER', 'STUDENT'].includes(userRole)) {
    redirect('/login');
  }

  switch (userRole) {
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
