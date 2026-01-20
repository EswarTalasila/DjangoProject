// E2E test: admin assessment update.
import { test, expect } from '@playwright/test';
import { env } from '../helpers/env';
import { apiCreateAssessment, apiUpdateAssessment } from '../helpers/api';
import { createAuthenticatedContext, loginViaApi } from '../helpers/ui';

// Test: admin sees updated assessment title in list.
test('admin sees updated assessment title in list', async ({ browser, request }) => {
  const adminSession = await loginViaApi(
    request,
    env.adminUsername,
    env.adminPassword
  );

  const originalTitle = `E2E Assessment ${Date.now()}`;
  const updatedTitle = `${originalTitle} Updated`;

  const created = await apiCreateAssessment(request, adminSession.token, originalTitle);
  await apiUpdateAssessment(request, adminSession.token, created.id, updatedTitle);

  const context = await createAuthenticatedContext(browser, adminSession);
  const page = await context.newPage();

  await page.goto('/assessments');
  await expect(
    page.getByRole('heading', { name: 'Assessments', level: 1 })
  ).toBeVisible();
  await expect(page.getByText(updatedTitle)).toBeVisible();

  await context.close();
});
