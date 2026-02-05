// E2E test: admin account flow.
import { test, expect } from '@playwright/test';
import { uniqueEmail } from '../helpers/api';
import { env } from '../helpers/env';
import {
  acknowledgeDialog,
  confirmDialog,
  createAuthenticatedContext,
  loginViaApi,
} from '../helpers/ui';

// Test: admin can create a teacher and reset the password.
test('admin can create a teacher and reset the password', async ({ browser, request }) => {
  test.setTimeout(120_000);

  const adminSession = await loginViaApi(
    request,
    env.adminUsername,
    env.adminPassword
  );

  const context = await createAuthenticatedContext(browser, adminSession);
  const page = await context.newPage();

  const teacherEmail = uniqueEmail('teacher');
  await page.goto('/account/create');
  await expect(page.getByRole('heading', { name: 'Add Account' })).toBeVisible();

  const closeInfoDialog = page.locator('.info-dialog .close-btn');
  if (await closeInfoDialog.isVisible()) {
    await closeInfoDialog.click();
  }

  await page.locator('#role').selectOption('teacher');
  await page.locator('#fname').fill('Play');
  await page.locator('#lname').fill('Teacher');
  await page.locator('#email').fill(teacherEmail);
  const createResponsePromise = page.waitForResponse((response) => {
    return response.url().includes('/auth/createuser');
  });
  await page.locator('#create-button').click();
  const createResponse = await createResponsePromise;
  expect(createResponse.status()).toBe(200);

  await acknowledgeDialog(page, 'Success');
  await page.waitForURL('**/account');
  await expect(page.getByRole('heading', { name: 'Accounts' })).toBeVisible();

  const teacherRow = page.locator('#teacher-list li', { hasText: teacherEmail });
  await expect(teacherRow).toBeVisible();
  await teacherRow.getByRole('button', { name: 'Reset Password' }).click();

  await confirmDialog(page, 'Confirm Password Reset');
  await acknowledgeDialog(page, 'Success');

  await context.close();
});
