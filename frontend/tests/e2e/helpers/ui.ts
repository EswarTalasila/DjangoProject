// Playwright helper utilities.
import type { APIRequestContext, Browser, BrowserContext, Page } from '@playwright/test';
import { expect } from '@playwright/test';
import { apiLogin } from './api';

export type AuthSession = {
  token: string;
  role: string;
  userId: string;
};

export async function createAuthenticatedContext(
  browser: Browser,
  session: AuthSession
): Promise<BrowserContext> {
  const context = await browser.newContext();
  await context.addInitScript(
    ([token, role, userId]) => {
      localStorage.setItem('token', token);
      localStorage.setItem('userRole', role);
      localStorage.setItem('userId', userId);
    },
    [session.token, session.role, session.userId]
  );
  return context;
}

export async function loginViaApi(
  request: APIRequestContext,
  username: string,
  password: string
): Promise<AuthSession> {
  const login = await apiLogin(request, username, password);
  return {
    token: login.accessToken,
    role: login.role,
    userId: login.id,
  };
}

export async function loginViaUi(
  page: Page,
  username: string,
  password: string
): Promise<void> {
  await page.goto('/login');
  await page.locator('#email').fill(username);
  await page.locator('#continue-btn').click();
  await page.locator('#password').fill(password);
  await page.locator('#login-button').click();
}

export async function confirmDialog(page: Page, title: string): Promise<void> {
  const dialog = page.locator('.dialog-container').filter({
    has: page.getByRole('heading', { name: title }),
  });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: 'Confirm' }).click();
}

export async function acknowledgeDialog(page: Page, title: string): Promise<void> {
  const dialog = page.locator('.dialog-container').filter({
    has: page.getByRole('heading', { name: title }),
  });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: 'OK' }).click();
}
