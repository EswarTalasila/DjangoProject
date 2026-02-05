// E2E test: admin assessment.
import { test, expect } from '@playwright/test';
import { env } from '../helpers/env';
import { apiCreateAssessment } from '../helpers/api';
import { createAuthenticatedContext, loginViaApi } from '../helpers/ui';

// Test: admin sees newly created assessment in list.
test('admin sees newly created assessment in list', async ({ browser, request }) => {
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
  await expect(
    page.getByRole('heading', { name: 'Assessments', level: 1 })
  ).toBeVisible();
  await expect(page.getByText(title)).toBeVisible();

  await context.close();
});
