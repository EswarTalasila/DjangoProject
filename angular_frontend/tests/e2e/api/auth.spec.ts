// E2E test: auth.
import { test, expect } from '@playwright/test';
import { env } from '../helpers/env';
import { apiCheckEmail, apiLogin, apiRegisterStudent, uniqueEmail } from '../helpers/api';

// Test: check-email returns existing user for admin.
test('check-email returns existing user for admin', async ({ request }) => {
  const result = await apiCheckEmail(request, env.adminUsername);
  expect(result).not.toBeNull();
  expect(result?.exists).toBeTruthy();
});

// Test: registers and logs in a new student.
test('registers and logs in a new student', async ({ request }) => {
  const username = uniqueEmail('student');
  await apiRegisterStudent(request, username, env.defaultStudentPassword, 'Student E2E');

  const login = await apiLogin(request, username, env.defaultStudentPassword);
  expect(login.accessToken).toBeTruthy();
  expect(login.role).toBe('STUDENT');
});
