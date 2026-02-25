import api from '@/lib/api';

export type PasswordResetIssueResponse = {
  requestId: number;
  targetUserId: number;
  targetRole: 'STUDENT' | 'TEACHER' | 'RESEARCHER';
  resetCode: string;
  expiresAt: string;
};

export type StaffUser = {
  id: number;
  name: string;
  username: string;
  email: string | null;
  role: 'TEACHER' | 'RESEARCHER' | 'STUDENT';
};

type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type MySudoGrantResponse = {
  hasSudo: boolean;
  canGrantSudo: boolean;
  permissions: string[];
  isStaff: boolean;
};

export async function issuePasswordResetCode(targetUserId: number): Promise<PasswordResetIssueResponse> {
  const response = await api.post<PasswordResetIssueResponse>('/auth/password-reset-codes', {
    targetUserId,
  });
  return response.data;
}

export async function listStaffUsers(): Promise<StaffUser[]> {
  const response = await api.get<PaginatedResponse<StaffUser>>('/users/staff');
  return response.data.results;
}

export async function getMySudoGrant(): Promise<MySudoGrantResponse> {
  const response = await api.get<MySudoGrantResponse>('/sudo-grants/me');
  return response.data;
}
