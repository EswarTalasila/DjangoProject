// E2E test: login ui.
import { test, expect } from '@playwright/test';
import { env } from '../helpers/env';
import { loginViaUi } from '../helpers/ui';

// Test: admin can log in via UI.
test('admin can log in via UI', async ({ page }) => {
  await loginViaUi(page, env.adminUsername, env.adminPassword);
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(
    page.getByRole('heading', { name: 'Visualization Dashboard', level: 1 })
  ).toBeVisible();
});
