import { redirect } from "next/navigation";
import { getSessionProfile } from "@/lib/auth-session";
import { ChangePasswordForm } from "@/components/settings/changePasswordForm";

export default async function SettingsPage() {
  const profile = await getSessionProfile();
  if (!profile) {
    redirect("/login");
  }

  return <ChangePasswordForm profile={profile} />;
}
