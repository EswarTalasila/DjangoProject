// Playwright helper utilities.
import type { APIRequestContext, APIResponse } from '@playwright/test';
import { env } from './env';

export type LoginResponse = {
  accessToken: string;
  role: string;
  id: string;
};

export function uniqueEmail(prefix: string): string {
  const stamp = Date.now();
  const nonce = Math.random().toString(36).slice(2, 8);
  return `${prefix}-${stamp}-${nonce}@example.com`;
}

export function authHeaders(token: string): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`,
  };
}

async function assertOk(response: APIResponse, message: string): Promise<void> {
  if (!response.ok()) {
    const body = await response.text();
    throw new Error(`${message}: ${body}`);
  }
}

export async function apiLogin(
  request: APIRequestContext,
  username: string,
  password: string
): Promise<LoginResponse> {
  const response = await request.post(`${env.apiURL}/auth/login`, {
    data: { username, password },
  });
  await assertOk(response, 'Login failed');
  return (await response.json()) as LoginResponse;
}

export async function apiCheckEmail(
  request: APIRequestContext,
  email: string
): Promise<{ exists: boolean; userId: number; needsPassword: boolean } | null> {
  const response = await request.post(`${env.apiURL}/auth/check-email`, {
    data: { email },
  });
  if (!response.ok()) {
    return null;
  }
  return (await response.json()) as { exists: boolean; userId: number; needsPassword: boolean };
}

export async function apiCreateAssessment(
  request: APIRequestContext,
  token: string,
  title: string
): Promise<{ id: number; questionId: number }>
{
  const response = await request.post(`${env.apiURL}/assessments/`, {
    headers: authHeaders(token),
    data: {
      title,
      gradingMode: 'AUTO',
      questions: [
        {
          type: 'SHORT_ANSWER',
          prompt: 'Describe your day',
          maxPoints: 5,
          data: { trim: true, caseSensitive: false },
        },
      ],
    },
  });
  await assertOk(response, 'Create assessment failed');
  const body = await response.json();
  const firstQuestion = Array.isArray(body.questions) ? body.questions[0] : undefined;
  const questionId = firstQuestion?.questionId ?? firstQuestion?.id;
  if (!questionId) {
    throw new Error('Created assessment missing questionId');
  }
  return { id: body.id, questionId };
}

export async function apiUpdateAssessment(
  request: APIRequestContext,
  token: string,
  assessmentId: number,
  title: string
): Promise<void> {
  const response = await request.put(`${env.apiURL}/assessments/${assessmentId}`, {
    headers: authHeaders(token),
    data: {
      title,
      gradingMode: 'AUTO',
      questions: [
        {
          type: 'SHORT_ANSWER',
          prompt: 'Updated prompt',
          maxPoints: 5,
          data: { trim: true, caseSensitive: false },
        },
      ],
    },
  });
  await assertOk(response, 'Update assessment failed');
}

export async function apiRegisterStudent(
  request: APIRequestContext,
  username: string,
  password: string,
  name = 'Student'
): Promise<void> {
  const response = await request.post(`${env.apiURL}/auth/register`, {
    data: { username, password, name },
  });
  await assertOk(response, 'Register student failed');
}

export async function apiCreateTeacher(
  request: APIRequestContext,
  token: string,
  username: string,
  password: string
): Promise<void> {
  const response = await request.post(`${env.apiURL}/auth/createuser`, {
    headers: authHeaders(token),
    data: {
      username,
      password,
      name: 'Teacher',
      role: 'ROLE_TEACHER',
    },
  });
  await assertOk(response, 'Create teacher failed');
}

export async function apiCreateCourse(
  request: APIRequestContext,
  token: string,
  name: string
): Promise<{ id: number }>
{
  const response = await request.post(`${env.apiURL}/courses/`, {
    headers: authHeaders(token),
    data: { name },
  });
  await assertOk(response, 'Create course failed');
  const body = await response.json();
  return { id: body.id };
}

export async function apiCreateStudent(
  request: APIRequestContext,
  token: string,
  name: string,
  username: string,
  password: string,
  courseId: number
): Promise<{ id: number }>
{
  const response = await request.post(`${env.apiURL}/students/`, {
    headers: authHeaders(token),
    data: {
      name,
      username,
      password,
      courseId,
      consent: true,
    },
  });
  await assertOk(response, 'Create student failed');
  const body = await response.json();
  return { id: body.id };
}

export async function apiCreateAssignment(
  request: APIRequestContext,
  token: string,
  assessmentId: number,
  courseId: number
): Promise<{ id: number }>
{
  const openAt = new Date(Date.now() - 60_000).toISOString();
  const response = await request.post(`${env.apiURL}/assignments/`, {
    headers: authHeaders(token),
    data: {
      assessmentId,
      audienceType: 'COURSE',
      courseId,
      openAt,
    },
  });
  await assertOk(response, 'Create assignment failed');
  const body = await response.json();
  return { id: body.id };
}

export async function apiSubmitAssignment(
  request: APIRequestContext,
  token: string,
  assignmentId: number,
  studentId: string,
  questionId: number
): Promise<void> {
  const response = await request.post(
    `${env.apiURL}/assignments/${assignmentId}/submissions`,
    {
      headers: authHeaders(token),
      data: {
        assignmentId,
        studentId: Number(studentId),
        status: 'SUBMITTED',
        answers: [
          {
            questionId,
            type: 'SHORT_ANSWER',
            data: { text: 'E2E Answer' },
          },
        ],
      },
    }
  );
  await assertOk(response, 'Submit assignment failed');
}

export async function apiCreateRubricAssessment(
  request: APIRequestContext,
  token: string,
  title: string
): Promise<{ id: number; questionIds: number[] }> {
  const response = await request.post(`${env.apiURL}/assessments/`, {
    headers: authHeaders(token),
    data: {
      title,
      gradingMode: 'RUBRIC',
      questions: [
        {
          type: 'SHORT_ANSWER',
          prompt: 'Rubric criterion',
          maxPoints: 5,
          data: { trim: true, caseSensitive: false },
        },
      ],
    },
  });
  await assertOk(response, 'Create rubric assessment failed');
  const body = await response.json();
  const questionIds = Array.isArray(body.questions)
    ? body.questions
        .map((question: { questionId?: number; id?: number }) => question.questionId ?? question.id)
        .filter((id: number | undefined): id is number => id !== undefined)
    : [];
  if (questionIds.length === 0) {
    throw new Error('Created rubric assessment missing questionIds');
  }
  return { id: body.id, questionIds };
}

export async function apiCreateManualAssessmentWithRubric(
  request: APIRequestContext,
  token: string,
  title: string,
  rubricId: number
): Promise<{ id: number; questionId: number }> {
  const response = await request.post(`${env.apiURL}/assessments/`, {
    headers: authHeaders(token),
    data: {
      title,
      gradingMode: 'MANUAL',
      rubricId,
      questions: [
        {
          type: 'SHORT_ANSWER',
          prompt: 'Describe your experience',
          maxPoints: 5,
          data: { trim: true, caseSensitive: false },
        },
      ],
    },
  });
  await assertOk(response, 'Create manual assessment failed');
  const body = await response.json();
  const firstQuestion = Array.isArray(body.questions) ? body.questions[0] : undefined;
  const questionId = firstQuestion?.questionId ?? firstQuestion?.id;
  if (!questionId) {
    throw new Error('Created manual assessment missing questionId');
  }
  return { id: body.id, questionId };
}
