import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import CourseDetailView from '@/components/courses/CourseDetailView';

type Params = { id: string };

export default async function CourseDetailPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.role as string;
  if (role !== 'TEACHER' && role !== 'RESEARCHER' && role !== 'STUDENT') {
    redirect('/dashboard');
  }

  const { id } = await params;
  const courseId = Number(id);
  if (Number.isNaN(courseId)) {
    redirect('/dashboard/courses');
  }

  return (
    <CourseDetailView
      courseId={courseId}
      userRole={role as 'TEACHER' | 'RESEARCHER' | 'STUDENT'}
      userId={Number(profile.id)}
    />
  );
}
