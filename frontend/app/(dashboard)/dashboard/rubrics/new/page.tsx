import { redirect } from 'next/navigation';
import { getSessionProfile } from '@/lib/auth-session';
import RubricBuilderForm from '@/components/rubrics/RubricBuilderForm';

export default async function NewRubricPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.role as string;
  const canManage = role === 'RESEARCHER' || Boolean(profile.isStaff);
  if (!canManage) {
    redirect('/dashboard/rubrics');
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Create Rubric</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Build a new rubric with criteria and scoring levels.
        </p>
      </div>
      <RubricBuilderForm mode="create" />
    </div>
  );
}
