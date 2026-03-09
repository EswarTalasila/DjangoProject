import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import VizCourseSummaryView from '@/components/visualizations/VizCourseSummaryView';

type Props = { params: Promise<{ courseId: string }> };

export default async function VizCoursePage({ params }: Props) {
  const profile = await getSessionProfile();
  if (!profile) redirect('/login');

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (!['TEACHER', 'RESEARCHER', 'ADMIN'].includes(role)) {
    redirect('/dashboard');
  }

  const { courseId } = await params;
  return <VizCourseSummaryView courseId={Number(courseId)} role={role} />;
}
