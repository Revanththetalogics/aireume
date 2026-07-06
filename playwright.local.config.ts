import { defineConfig, devices } from '@playwright/test';

/**
 * Local config for running E2E against a locally-served frontend dev server.
 *
 * By default it runs only the unauthenticated login-page specs (auth-workflow),
 * which exercise real browser behaviour of the UI without needing the backend
 * logged-in state. To run the authenticated specs locally, start the backend on
 * :8000, seed a user, and remove the `grep` / add the `setup` project.
 *
 *   npx playwright test --config=playwright.local.config.ts
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  // Only the unauthenticated login-page flow by default.
  grep: /Auth workflow \(login page\)/,
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium-local',
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
