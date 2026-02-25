import api from '@/lib/api';

type CreatedCode = {
  id?: number;
  code?: string | null;
  codeType?: 'STUDENT' | 'TEACHER' | 'RESEARCHER';
  expiresAt?: string;
};

type CreateCodesResponse = {
  count: number;
  codes: CreatedCode[];
};

export type CreateRegistrationCodesRequest = {
  codeType: 'STUDENT' | 'TEACHER' | 'RESEARCHER';
  count: number;
  usesPerCode: number;
  expiresAt: string;
  courseId?: number;
};

export async function createRegistrationCodes(
  payload: CreateRegistrationCodesRequest,
): Promise<CreateCodesResponse> {
  const response = await api.post<CreateCodesResponse>('/codes', payload);
  return response.data;
}

export async function createStudentRegistrationCode(courseId: number): Promise<string> {
  const expiresAt = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString();
  const response = await createRegistrationCodes({
    codeType: 'STUDENT',
    count: 1,
    usesPerCode: 1,
    expiresAt,
    courseId,
  });
  const code = response.codes?.[0]?.code;
  if (!code) {
    throw new Error('Registration code was not returned by the server.');
  }
  return code;
}
