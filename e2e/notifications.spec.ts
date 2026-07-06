import { test, expect } from '@playwright/test';

/**
 * Notification system (new NotificationBell + context). The bell lives in the
 * top nav, opens a dropdown, and shows a "caught up" empty state when there are
 * no notifications.
 */
test.describe('Notification bell', () => {
  test('bell is present in the navigation and opens a dropdown', async ({ page }) => {
    await page.goto('/home');
    await page.waitForLoadState('networkidle');

    const bell = page.getByRole('button', { name: /notifications/i }).first();
    await expect(bell).toBeVisible({ timeout: 15000 });

    await bell.click();
    // Either shows a list or the caught-up empty state
    const menu = page.getByRole('menu');
    await expect(menu).toBeVisible({ timeout: 5000 });
    await expect(
      menu.getByText(/all caught up|notifications/i).first()
    ).toBeVisible();
  });

  test('dropdown closes on Escape', async ({ page }) => {
    await page.goto('/home');
    await page.waitForLoadState('networkidle');

    const bell = page.getByRole('button', { name: /notifications/i }).first();
    await bell.click();
    await expect(page.getByRole('menu')).toBeVisible({ timeout: 5000 });

    await page.keyboard.press('Escape');
    await expect(page.getByRole('menu')).toHaveCount(0);
  });
});
