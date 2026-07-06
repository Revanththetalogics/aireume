import { test, expect } from '@playwright/test';

// These run WITHOUT the saved auth state so we can exercise the login page itself.
test.use({ storageState: { cookies: [], origins: [] } });

test.describe('Auth workflow (login page)', () => {
  test('renders workspace, email and password fields', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    await expect(page.getByPlaceholder('your-company')).toBeVisible({ timeout: 10000 });
    await expect(page.getByPlaceholder('you@company.com')).toBeVisible();
    await expect(page.getByPlaceholder('••••••••')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('password visibility can be toggled (accessible control)', async ({ page }) => {
    await page.goto('/login');
    const pw = page.getByPlaceholder('••••••••');
    await expect(pw).toHaveAttribute('type', 'password');

    await page.getByRole('button', { name: /show password/i }).click();
    await expect(pw).toHaveAttribute('type', 'text');

    await page.getByRole('button', { name: /hide password/i }).click();
    await expect(pw).toHaveAttribute('type', 'password');
  });

  test('invalid credentials surface an error message', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('your-company').fill('does-not-exist');
    await page.getByPlaceholder('you@company.com').fill('nobody@example.com');
    await page.getByPlaceholder('••••••••').fill('WrongPassword123!');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should show an error banner rather than navigating away
    await expect(page.getByText(/invalid|incorrect|not found|failed/i).first())
      .toBeVisible({ timeout: 15000 });
  });

  test('offers a link to create a workspace', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('link', { name: /create workspace/i })).toBeVisible();
  });
});
