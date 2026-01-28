// E2E test: admin assessment delete.
import { test, expect } from '@playwright/test';
import { env } from '../helpers/env';
import { apiCreateAssessment } from '../helpers/api';
import { acknowledgeDialog, confirmDialog, createAuthenticatedContext, loginViaApi } from '../helpers/ui';

// Test: admin can delete an assessment from the list.
test('admin can delete an assessment from the list', async ({ browser, request }) => {
  const adminSession = await loginViaApi(
    request,
    env.adminUsername,
    env.adminPassword
  );

  const title = `E2E Assessment ${Date.now()}`;
  await apiCreateAssessment(request, adminSession.token, title);

  const context = await createAuthenticatedContext(browser, adminSession);
  const page = await context.newPage();

  await page.goto('/assessments');
  const card = page.locator('.assessment-card').filter({ hasText: title });
  await expect(card).toBeVisible();

  await card.getByRole('button', { name: 'Delete Assessment' }).click();
  await confirmDialog(page, 'Confirm Deletion');
  await acknowledgeDialog(page, 'Success');

  await expect(page.locator('.assessment-card').filter({ hasText: title })).toHaveCount(0);

  await context.close();
});
