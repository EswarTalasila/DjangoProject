import api from '@/lib/api';

type CreatedCode = {
  code?: string | null;
};

type CreateCodesResponse = {
  count: number;
  codes: CreatedCode[];
};

export async function createStudentRegistrationCode(courseId: number): Promise<string> {
  const expiresAt = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString();
  const response = await api.post<CreateCodesResponse>('/codes', {
    codeType: 'STUDENT',
    count: 1,
    usesPerCode: 1,
    expiresAt,
    courseId,
  });
  const code = response.data.codes?.[0]?.code;
  if (!code) {
    throw new Error('Registration code was not returned by the server.');
  }
  return code;
}
