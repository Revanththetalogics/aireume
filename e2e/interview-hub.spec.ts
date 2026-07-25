import { test, expect } from '@playwright/test';

/**
 * Interview-flow consolidation (P1-UX-09): /ai-interviews is the unified hub;
 * /voice-screening and /recruiter-interviews are advanced sub-pages reachable
 * from the hub's config tab and each carries a breadcrumb back to the hub.
 */
test.describe('AI Interview hub', () => {
  test('hub page loads', async ({ page }) => {
    await page.goto('/ai-interviews');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText(/interview/i).first()).toBeVisible({ timeout: 15000 });
  });

  test('voice screening page has a breadcrumb back to the hub', async ({ page }) => {
    await page.goto('/voice-screening');
    await page.waitForLoadState('networkidle');

    const breadcrumb = page.getByRole('button', { name: /ai interviews/i }).first();
    await expect(breadcrumb).toBeVisible({ timeout: 15000 });
    await breadcrumb.click();
    await expect(page).toHaveURL(/.*ai-interviews.*/);
  });

  test('recruiter interviews page has a breadcrumb back to the hub', async ({ page }) => {
    await page.goto('/recruiter-interviews');
    await page.waitForLoadState('networkidle');

    const breadcrumb = page.getByRole('button', { name: /ai interviews/i }).first();
    await expect(breadcrumb).toBeVisible({ timeout: 15000 });
    await breadcrumb.click();
    await expect(page).toHaveURL(/.*ai-interviews.*/);
  });

  test('hub config tab links out to advanced engine settings', async ({ page }) => {
    await page.goto('/ai-interviews');
    await page.waitForLoadState('networkidle');

    const settingsLink = page.getByRole('link', { name: /interview settings/i }).first();
    await expect(settingsLink).toBeVisible({ timeout: 15000 });
    await expect(settingsLink).toHaveAttribute('href', /settings\?tab=interviews/);
  });
});
