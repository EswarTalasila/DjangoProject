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
        <header className="h-16 border-b bg-card flex items-center justify-between px-8">
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
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

        <main className="flex-1 overflow-y-auto p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
