// E2E test: error paths.
import { test, expect } from '@playwright/test';
import {
  apiCreateAssessment,
  apiCreateAssignment,
  apiCreateCourse,
  apiCreateStudent,
  apiCreateTeacher,
  authHeaders,
  uniqueEmail,
} from '../helpers/api';
import { env } from '../helpers/env';
import { loginViaApi } from '../helpers/ui';

// Test: api error paths return expected status codes.
test('api error paths return expected status codes', async ({ request }) => {
  const unauthorized = await request.get(`${env.apiURL}/courses/`);
  expect(unauthorized.status()).toBe(401);

  const adminSession = await loginViaApi(
    request,
    env.adminUsername,
    env.adminPassword
  );

  const teacherEmail = uniqueEmail('teacher');
  await apiCreateTeacher(
    request,
    adminSession.token,
    teacherEmail,
    env.defaultTeacherPassword
  );
  const teacherSession = await loginViaApi(
    request,
    teacherEmail,
    env.defaultTeacherPassword
  );

  const forbiddenCreate = await request.post(`${env.apiURL}/auth/createuser`, {
    headers: authHeaders(teacherSession.token),
    data: {
      username: uniqueEmail('admin'),
      name: 'Unauthorized Admin',
      role: 'ROLE_ADMIN',
    },
  });
  expect(forbiddenCreate.status()).toBe(403);

  const invalidCourse = await request.post(`${env.apiURL}/courses/`, {
    headers: authHeaders(teacherSession.token),
    data: { name: '' },
  });
  expect(invalidCourse.status()).toBe(400);

  const course = await apiCreateCourse(
    request,
    teacherSession.token,
    `E2E Course ${Date.now()}`
  );

  const studentEmail = uniqueEmail('student');
  await apiCreateStudent(
    request,
    teacherSession.token,
    'Student Error',
    studentEmail,
    env.defaultStudentPassword,
    course.id
  );
  const studentSession = await loginViaApi(
    request,
    studentEmail,
    env.defaultStudentPassword
  );

  const assessment = await apiCreateAssessment(
    request,
    adminSession.token,
    `E2E Assessment ${Date.now()}`
  );
  const assignment = await apiCreateAssignment(
    request,
    teacherSession.token,
    assessment.id,
    course.id
  );

  const studentForbidden = await request.get(
    `${env.apiURL}/assignments/${assignment.id}/submissions`,
    {
      headers: authHeaders(studentSession.token),
    }
  );
  expect(studentForbidden.status()).toBe(403);

  const notFound = await request.get(`${env.apiURL}/assessments/999999`, {
    headers: authHeaders(adminSession.token),
  });
  expect(notFound.status()).toBe(404);
});
