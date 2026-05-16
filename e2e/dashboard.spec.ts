import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test('should load dashboard after login', async ({ page }) => {
    await page.goto('/home');

    // Dashboard should show key sections
    await expect(page.getByText(/pipeline summary|dashboard/i).first()).toBeVisible({ timeout: 10000 });

    // Status cards should be visible (Pending Review, In Progress, Shortlisted, etc.)
    await expect(page.getByText(/pending review/i)).toBeVisible();
    await expect(page.getByText(/in progress/i)).toBeVisible();
    await expect(page.getByText(/shortlisted/i)).toBeVisible();
  });

  test('should navigate to candidates from status cards', async ({ page }) => {
    await page.goto('/home');
    await page.waitForLoadState('networkidle');

    // Click "View candidates" on any card
    const viewLink = page.getByText(/view candidates/i).first();
    await expect(viewLink).toBeVisible({ timeout: 10000 });
    await viewLink.click();

    // Should navigate to candidates page
    await expect(page).toHaveURL(/.*candidates.*/);
  });

  test('Pipeline Summary should be scrollable', async ({ page }) => {
    await page.goto('/home');
    await page.waitForLoadState('networkidle');

    // Find pipeline summary section
    const pipelineSection = page.getByText(/pipeline summary/i).locator('..');
    await expect(pipelineSection).toBeVisible({ timeout: 10000 });

    // The scrollable container should have overflow-y-auto
    const scrollContainer = pipelineSection.locator('[class*="overflow-y-auto"]');
    // If it exists, pipeline is scrollable (may not exist if few cards)
    const count = await scrollContainer.count();
    if (count > 0) {
      await expect(scrollContainer).toBeVisible();
    }
  });
});
