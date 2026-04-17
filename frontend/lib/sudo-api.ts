import api from '@/lib/api';

export type SudoGrantListItem = {
  id: number;
  user: { id: number; username: string; name: string };
  permissions: string[];
  canGrantSudo: boolean;
  grantedAt: string;
};

export type GrantSudoPayload = {
  user_id: number;
  permissions: string[];
  can_grant_sudo?: boolean;
};

export type GrantSudoResponse = {
  message: string;
  grant_id: number;
};

export async function listSudoGrants(): Promise<SudoGrantListItem[]> {
  const response = await api.get<SudoGrantListItem[]>('/sudo-grants');
  return response.data;
}

export async function grantSudo(payload: GrantSudoPayload): Promise<GrantSudoResponse> {
  const response = await api.post<GrantSudoResponse>('/sudo-grants', payload);
  return response.data;
}

export async function revokeSudoGrant(grantId: number): Promise<void> {
  await api.delete(`/sudo-grants/${grantId}`);
}
