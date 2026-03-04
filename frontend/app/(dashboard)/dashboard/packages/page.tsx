import { redirect } from 'next/navigation';

import { getSessionProfile, getSudoCapabilities } from '@/lib/auth-session';

export default async function PackagesPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  const role = profile.isStaff ? 'ADMIN' : (profile.role as string);
  if (!['TEACHER', 'ADMIN'].includes(role)) {
    if (role !== 'RESEARCHER') {
      redirect('/dashboard');
    }
    const sudo = await getSudoCapabilities();
    const canExport = sudo?.permissions?.includes('EXPORT_IDENTIFIABLE') === true;
    if (!canExport) {
      redirect('/dashboard');
    }
  }

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Package Workspaces
        </h1>
        <p className="text-muted-foreground mt-1">
          FR-16 backend is available. Frontend workspace builder is the next UI pass.
        </p>
      </div>

      <div className="rounded-sm border border-border bg-card p-6">
        <h2 className="text-lg font-semibold text-foreground mb-2">Current Status</h2>
        <p className="text-sm text-muted-foreground">
          Package APIs for workspace CRUD, validation, build jobs, and artifact download are in
          place. This page is a temporary placeholder while the drag/drop workspace UI is built.
        </p>
      </div>
    </div>
  );
}
