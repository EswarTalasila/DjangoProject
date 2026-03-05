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

export type StudentUser = {
  id: number;
  name: string;
  username: string;
  courses: { id: number; name: string }[];
};

export type MySudoGrantResponse = {
  hasSudo: boolean;
  canGrantSudo: boolean;
  permissions: string[];
  isStaff: boolean;
};

/** POST /auth/password-reset-codes — Generate a reset code for a target user (admin/sudo only). */
export async function issuePasswordResetCode(
  targetUserId: number,
): Promise<PasswordResetIssueResponse> {
  const response = await api.post<PasswordResetIssueResponse>(
    "/auth/password-reset-codes",
    { targetUserId },
  );
  return response.data;
}

/** POST /auth/password-resets — Complete a password reset using a valid reset code. */
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

/** GET /users/staff — List all staff users (teachers and researchers). */
export async function listStaffUsers(): Promise<StaffUser[]> {
  const response = await api.get<Paginated<StaffUser> | StaffUser[]>(
    "/users/staff",
  );
  const data = response.data;
  if (Array.isArray(data)) return data;
  return data.results ?? [];
}

/** GET /users/students — Search students with optional query and course filter. */
export async function listStudents(params?: {
  q?: string;
  courseId?: number;
}): Promise<StudentUser[]> {
  const query = new URLSearchParams();
  if (params?.q) query.set("q", params.q);
  if (params?.courseId) query.set("courseId", String(params.courseId));
  const qs = query.toString();
  const url = qs ? `/users/students?${qs}` : "/users/students";
  const response = await api.get<
    { count: number; results: StudentUser[] } | StudentUser[]
  >(url);
  const data = response.data;
  if (Array.isArray(data)) return data;
  return data.results ?? [];
}

/** GET /sudo-grants/me — Fetch the current user's sudo grant status. */
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

/** POST /auth/reset-code-validations — Verify that a reset code is valid before use. */
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

/** PATCH /auth/password — Change the current user's password (requires current password). */
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
