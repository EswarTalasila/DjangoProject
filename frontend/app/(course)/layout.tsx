import { redirect } from 'next/navigation';
import { Sidebar } from '@/components/layout/sidebar';
import { getSessionProfile } from '@/lib/auth-session';

export default async function CoursesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect('/login');
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar />
      <div className="flex flex-col flex-1">
        <header className="h-16 border-b bg-white flex items-center justify-between px-8">
          <h2 className="text-sm font-medium text-slate-500 uppercase tracking-wider">
            Ready, Set, Resilience
          </h2>
          <div className="flex items-center gap-4">
             <div className="h-8 w-8 rounded-full bg-slate-200" />
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
