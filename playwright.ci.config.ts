import { defineConfig, devices } from '@playwright/test';

/**
 * CI config: deterministic, no backend or secrets required.
 *
 * Serves the built frontend with `vite preview` and runs only the
 * unauthenticated login-page specs (real Chromium, real DOM). Authenticated
 * specs are intentionally excluded here — they need the full stack and run
 * locally (playwright.local.config.ts) or against staging (playwright.config.ts).
 *
 *   npx playwright test --config=playwright.ci.config.ts
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  // Only the unauthenticated login-page flow — no backend needed.
  grep: /Auth workflow \(login page\)/,
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium-ci',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    // The CI job runs `npm run build` first; here we just serve the output.
    command: 'npm run preview -- --port 4173 --strictPort',
    cwd: './app/frontend',
    url: 'http://localhost:4173',
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
