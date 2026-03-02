import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import AssessmentBuilderForm from '@/components/assessments/AssessmentBuilderForm';

export default async function EditAssessmentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.role as string;
  const canManage = role === 'RESEARCHER' || Boolean(profile.isStaff);
  if (!canManage) {
    redirect('/dashboard/assessments');
  }

  const { id } = await params;
  const assessmentId = Number(id);
  if (Number.isNaN(assessmentId)) {
    redirect('/dashboard/assessments');
  }

  return (
    <div className="space-y-6 p-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Edit Assessment</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Modify the assessment template and its questions.
        </p>
      </div>
      <AssessmentBuilderForm mode="edit" assessmentId={assessmentId} />
    </div>
  );
}
