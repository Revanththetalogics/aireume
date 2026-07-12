import { defineConfig, devices } from '@playwright/test';

/**
 * E2E onboarding flow — register through first analysis.
 *
 * Start the backend first with E2E_TEST_MODE=1:
 *   E2E_TEST_MODE=1 uvicorn app.backend.main:app --reload --port 8000
 *
 *   npx playwright test --config=playwright.onboarding.config.ts
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  grep: /Onboarding flow/,
  timeout: 120_000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium-onboarding',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    cwd: './app/frontend',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
