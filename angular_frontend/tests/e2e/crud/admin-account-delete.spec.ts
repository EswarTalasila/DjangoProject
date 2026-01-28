// E2E test: admin account delete.
import { test, expect } from '@playwright/test';
import { env } from '../helpers/env';
import { apiCreateTeacher, uniqueEmail } from '../helpers/api';
import { acknowledgeDialog, confirmDialog, createAuthenticatedContext, loginViaApi } from '../helpers/ui';

// Test: admin can delete a teacher account.
test('admin can delete a teacher account', async ({ browser, request }) => {
  const adminSession = await loginViaApi(
    request,
    env.adminUsername,
    env.adminPassword
  );

  const teacherEmail = uniqueEmail('teacher');
  await apiCreateTeacher(request, adminSession.token, teacherEmail, env.defaultTeacherPassword);

  const context = await createAuthenticatedContext(browser, adminSession);
  const page = await context.newPage();

  await page.goto('/account');
  await expect(page.getByRole('heading', { name: 'Accounts' })).toBeVisible();

  const teacherList = page.locator('#teacher-list');
  const teacherRow = teacherList.locator('.user-item').filter({ hasText: teacherEmail });
  await expect(teacherRow).toBeVisible();

  await teacherRow.getByRole('button', { name: 'Delete' }).click();
  await confirmDialog(page, 'Confirm Deletion');
  await acknowledgeDialog(page, 'Success');

  await expect(teacherList.locator('.user-item').filter({ hasText: teacherEmail })).toHaveCount(0);

  await context.close();
});
