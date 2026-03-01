import api from '@/lib/api';

type CreatedCode = {
  id?: number;
  code?: string | null;
  codeType?: 'STUDENT' | 'TEACHER' | 'RESEARCHER';
  maxUses?: number;
  expiresAt?: string;
};

type CreateCodesResponse = {
  count: number;
  codes: CreatedCode[];
};

export type RegistrationCodeType = 'STUDENT' | 'TEACHER' | 'RESEARCHER';

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
