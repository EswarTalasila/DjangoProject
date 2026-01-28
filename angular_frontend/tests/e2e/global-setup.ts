// Playwright global setup for E2E tests.
import { env } from './helpers/env';

async function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function check(url: string): Promise<boolean> {
  try {
    const response = await fetch(url, { method: 'GET' });
    return response.ok;
  } catch {
    return false;
  }
}

async function globalSetup(): Promise<void> {
  const timeoutMs = Number(process.env.E2E_WAIT_TIMEOUT_MS || 120_000);
  const start = Date.now();

  const targets = [`${env.baseURL}/login`, env.baseURL];

  while (Date.now() - start < timeoutMs) {
    for (const target of targets) {
      if (await check(target)) {
        return;
      }
    }
    await wait(1000);
  }

  throw new Error(`E2E server not ready at ${env.baseURL}`);
}

export default globalSetup;
