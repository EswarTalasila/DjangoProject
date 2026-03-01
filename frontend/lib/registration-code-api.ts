import api from '@/lib/api';

export type RegistrationCodeType = 'STUDENT' | 'TEACHER' | 'RESEARCHER';

export type RegistrationCodeStatus = 'ACTIVE' | 'EXHAUSTED' | 'EXPIRED' | 'REVOKED' | 'ARCHIVED';

export type RegistrationCode = {
  id: number;
  code: string | null;
  codePrefix: string;
  codeType: RegistrationCodeType;
  status: RegistrationCodeStatus;
  maxUses: number;
  timesUsed: number;
  usesRemaining: number;
  expiresAt: string;
  isActive: boolean;
  courseId: number | null;
  courseName: string | null;
  metadata: Record<string, unknown> | null;
  createdByUserId: number;
  createdAt: string;
  archivedAt: string | null;
};

export type RegistrationCodeListResponse = {
  count: number;
  next: string | null;
  previous: string | null;
  results: RegistrationCode[];
};

type CreateCodesResponse = {
  count: number;
  codes: RegistrationCode[];
};

export type CreateRegistrationCodeInput = {
  codeType: RegistrationCodeType;
  count?: number;
  usesPerCode: number;
  expiresAt: string;
  courseId?: number;
};

export async function createRegistrationCodes(
  payload: CreateRegistrationCodeInput,
): Promise<CreateCodesResponse> {
  const response = await api.post<CreateCodesResponse>('/codes', {
    codeType: payload.codeType,
    count: payload.count ?? 1,
    usesPerCode: payload.usesPerCode,
    expiresAt: payload.expiresAt,
    ...(payload.courseId ? { courseId: payload.courseId } : {}),
  });
  return response.data;
}

export type JoinCourseResponse = {
  message: string;
  courseId: number;
  alreadyEnrolled: boolean;
};

export async function joinCourseByCode(code: string): Promise<JoinCourseResponse> {
  const response = await api.post<JoinCourseResponse>('/enrollments', { code });
  return response.data;
}

export async function createStudentRegistrationCode(
  courseId: number,
  options?: { usesPerCode?: number; expiresAt?: string },
): Promise<string> {
  const response = await createRegistrationCodes({
    codeType: 'STUDENT',
    count: 1,
    usesPerCode: options?.usesPerCode ?? 1,
    expiresAt:
      options?.expiresAt ?? new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString(),
    courseId,
  });
  const code = response.codes?.[0]?.code;
  if (!code) {
    throw new Error('Registration code was not returned by the server.');
  }
  return code;
}

export async function listRegistrationCodes(params?: {
  status?: RegistrationCodeStatus;
  codeType?: RegistrationCodeType;
  includeArchived?: boolean;
}): Promise<RegistrationCodeListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.codeType) query.set('codeType', params.codeType);
  if (params?.includeArchived) query.set('includeArchived', 'true');
  const qs = query.toString();
  const response = await api.get<RegistrationCodeListResponse>(`/codes${qs ? `?${qs}` : ''}`);
  return response.data;
}

export async function getRegistrationCode(id: number): Promise<RegistrationCode> {
  const response = await api.get<RegistrationCode>(`/codes/${id}`);
  return response.data;
}

export async function updateRegistrationCodeStatus(
  id: number,
  status: 'REVOKED' | 'ARCHIVED',
): Promise<RegistrationCode> {
  const response = await api.patch<RegistrationCode>(`/codes/${id}`, { status });
  return response.data;
}
