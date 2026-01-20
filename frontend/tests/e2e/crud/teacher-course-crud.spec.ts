// E2E test: teacher course crud.
import { test, expect } from '@playwright/test';
import { env } from '../helpers/env';
import { apiCreateTeacher, uniqueEmail } from '../helpers/api';
import { acknowledgeDialog, confirmDialog, createAuthenticatedContext, loginViaApi } from '../helpers/ui';

// Test: teacher can create and delete a course.
test('teacher can create and delete a course', async ({ browser, request }) => {
  const adminSession = await loginViaApi(
    request,
    env.adminUsername,
    env.adminPassword
  );

  const teacherEmail = uniqueEmail('teacher');
  await apiCreateTeacher(request, adminSession.token, teacherEmail, env.defaultTeacherPassword);
  const teacherSession = await loginViaApi(request, teacherEmail, env.defaultTeacherPassword);

  const context = await createAuthenticatedContext(browser, teacherSession);
  const page = await context.newPage();

  const courseName = `E2E Course ${Date.now()}`;

  await page.goto('/course/create');
  await page.locator('#courseName').fill(courseName);
  await page.locator('#create-button').click();
  await acknowledgeDialog(page, 'Success');

  await expect(page.getByRole('heading', { name: 'My Courses' })).toBeVisible();
  const courseCard = page.locator('.course-card').filter({ hasText: courseName });
  await expect(courseCard).toBeVisible();

  await courseCard.getByRole('button', { name: 'Delete' }).click();
  await confirmDialog(page, 'Confirm Deletion');
  await acknowledgeDialog(page, 'Success');

  await expect(page.locator('.course-card').filter({ hasText: courseName })).toHaveCount(0);

  await context.close();
});
