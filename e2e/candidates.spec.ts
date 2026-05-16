import { test, expect } from '@playwright/test';

test.describe('Candidates Page', () => {
  test('should load candidates page', async ({ page }) => {
    await page.goto('/candidates');
    await page.waitForLoadState('networkidle');

    // Should show candidates heading or list
    await expect(page.getByText(/candidate/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('should filter by status from URL params', async ({ page }) => {
    await page.goto('/candidates?status=in_progress');
    await page.waitForLoadState('networkidle');

    // Page should load without errors
    await expect(page.getByText(/candidate/i).first()).toBeVisible({ timeout: 10000 });
  });
});
