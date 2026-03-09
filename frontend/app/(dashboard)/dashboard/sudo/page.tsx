import { redirect } from 'next/navigation';
import { getSessionProfile, getSudoCapabilities } from '@/lib/auth-session';
import SudoDelegationView from '@/components/sudo/SudoDelegationView';

export default async function SudoPage() {
  const profile = await getSessionProfile();
  if (!profile) redirect('/login');
  if (profile.role !== 'RESEARCHER') redirect('/dashboard');
  const sudo = await getSudoCapabilities();
  if (!sudo?.canGrantSudo) redirect('/dashboard');
  const currentUserId = Number(profile.id);
  return (
    <SudoDelegationView
      currentUserId={Number.isFinite(currentUserId) ? currentUserId : null}
    />
  );
}
