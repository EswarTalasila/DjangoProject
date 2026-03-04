import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import CoursesListView from '@/components/courses/CoursesListView';

export default async function CoursesPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.role as string;
  if (role !== 'TEACHER' && role !== 'STUDENT') {
    redirect('/dashboard');
  }

  return <CoursesListView userRole={role as 'TEACHER' | 'STUDENT'} />;
}
