import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '.auth/user.json');

// Credentials are overridable via env so this file needn't hardcode secrets.
const E2E_WORKSPACE = process.env.E2E_WORKSPACE || 'thetalogics';
const E2E_EMAIL = process.env.E2E_EMAIL || 'revanth.a@thetalogics.com';
const E2E_PASSWORD = process.env.E2E_PASSWORD || 'Admin@123';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');

  // The login form now requires a workspace slug in addition to email/password.
  // Placeholders (not labels) are the stable selectors on this page.
  await page.getByPlaceholder('your-company').fill(E2E_WORKSPACE);
  await page.getByPlaceholder('you@company.com').fill(E2E_EMAIL);
  await page.getByPlaceholder('••••••••').fill(E2E_PASSWORD);
  await page.getByRole('button', { name: /sign in|log in|login/i }).click();

  // Wait for redirect to dashboard/home
  await page.waitForURL('**/home**', { timeout: 15000 }).catch(() => {
    // Might redirect to /analyze or / instead
    return page.waitForURL('**/', { timeout: 5000 });
  });

  // Verify logged in - look for user avatar or nav element
  await expect(page.locator('nav, header').first()).toBeVisible();

  // Save auth state
  await page.context().storageState({ path: authFile });
});
