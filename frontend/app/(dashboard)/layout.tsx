import { SidebarWrapper } from "@/components/layout/sidebarWrapper";
import { redirect } from "next/navigation";
import { getSessionProfile } from "@/lib/auth-session";
import { UserAvatarMenu } from "@/components/layout/userAvatarMenu";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect("/login");
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <SidebarWrapper />
      <div className="flex flex-col flex-1">
        <header className="flex h-16 items-center justify-between border-b bg-card px-4 md:px-8">
          <h2 className="ml-12 text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground md:ml-0 md:text-sm md:tracking-wider">
            Ready, Set, Resilience
          </h2>
          <div className="flex items-center gap-4">
            <UserAvatarMenu
              name={profile.name}
              username={profile.username}
              role={profile.role}
            />
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
