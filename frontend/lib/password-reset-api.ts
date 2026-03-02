import api from "@/lib/api";

type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type PasswordResetIssueResponse = {
  requestId: number;
  targetUserId: number;
  targetRole: "STUDENT" | "TEACHER" | "RESEARCHER";
  resetCode: string;
  expiresAt: string;
};

export type PasswordResetCompleteResponse = {
  message: string;
};

export type StaffUser = {
  id: number;
  name: string;
  username: string;
  email: string | null;
  role: "TEACHER" | "RESEARCHER" | "STUDENT";
};

export type MySudoGrantResponse = {
  hasSudo: boolean;
  canGrantSudo: boolean;
  permissions: string[];
  isStaff: boolean;
};

export async function issuePasswordResetCode(
  targetUserId: number,
): Promise<PasswordResetIssueResponse> {
  const response = await api.post<PasswordResetIssueResponse>(
    "/auth/password-reset-codes",
    { targetUserId },
  );
  return response.data;
}

export async function completePasswordReset(payload: {
  identifier: string;
  resetCode: string;
  newPassword: string;
  confirmPassword: string;
}): Promise<PasswordResetCompleteResponse> {
  const response = await api.post<PasswordResetCompleteResponse>(
    "/auth/password-resets",
    payload,
  );
  return response.data;
}

export async function listStaffUsers(): Promise<StaffUser[]> {
  const response = await api.get<Paginated<StaffUser> | StaffUser[]>(
    "/users/staff",
  );
  const data = response.data;
  if (Array.isArray(data)) return data;
  return data.results ?? [];
}

export async function getMySudoGrant(): Promise<MySudoGrantResponse> {
  const response = await api.get<MySudoGrantResponse>("/sudo-grants/me");
  return response.data;
}

export type ResetCodeValidationResponse = {
  valid: boolean;
  requestId: number;
  expiresAt: string;
};

export type ChangePasswordResponse = {
  message: string;
};

export async function validateResetCode(
  identifier: string,
  resetCode: string,
): Promise<ResetCodeValidationResponse> {
  const response = await api.post<ResetCodeValidationResponse>(
    "/auth/reset-code-validations",
    { identifier, resetCode },
  );
  return response.data;
}

export async function changePassword(payload: {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}): Promise<ChangePasswordResponse> {
  const response = await api.patch<ChangePasswordResponse>(
    "/auth/password",
    payload,
  );
  return response.data;
}
