import { Sidebar } from "@/components/layout/sidebar";
import { SidebarWrapper } from "@/components/layout/sidebarWrapper";
import { cookies } from "next/headers"; // Import cookies
import { redirect } from "next/navigation"; // Import redirect

export default async function DashboardLayout({ // Make this async
  children,
}: {
  children: React.ReactNode;
}) {
  // 1. Check for the token
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");

  // 2. If no token exists, redirect to login
  if (!token) {
    redirect("/login");
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <SidebarWrapper />
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