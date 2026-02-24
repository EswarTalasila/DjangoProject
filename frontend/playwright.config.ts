import { defineConfig } from "@playwright/test";

const rawBaseURL = process.env.E2E_BASE_URL || "http://frontend:3000";
const baseURL = rawBaseURL
  .replace("localhost:3000", "frontend:3000")
  .replace("127.0.0.1:3000", "frontend:3000");

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: 1,
  timeout: 60_000,
  use: {
    baseURL,
    trace: "on-first-retry",
    headless: true,
  },
});
