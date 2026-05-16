import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '.auth/user.json');

setup('authenticate', async ({ page }) => {
  await page.goto('/login');

  // Fill login form
  await page.getByPlaceholder(/email/i).fill('revanth.a@thetalogics.com');
  await page.getByPlaceholder(/password/i).fill('Admin@123');
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
