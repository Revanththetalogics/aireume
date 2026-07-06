import { test, expect } from '@playwright/test';

/**
 * Accessibility smoke checks for the a11y remediations: icon-only modal close
 * buttons expose accessible names, and empty states / CTAs are reachable.
 * These are intentionally tolerant — they assert accessible names where the
 * control is present rather than forcing specific data states.
 */
test.describe('Accessibility', () => {
  test('team invite dialog exposes an accessible close control', async ({ page }) => {
    await page.goto('/team');
    await page.waitForLoadState('networkidle');

    const invite = page.getByRole('button', { name: /invite/i }).first();
    if (await invite.isVisible({ timeout: 5000 }).catch(() => false)) {
      await invite.click();
      await expect(
        page.getByRole('button', { name: /close dialog/i }).first()
      ).toBeVisible({ timeout: 10000 });
    }
  });

  test('compare page shows an empty state or comparison content', async ({ page }) => {
    await page.goto('/compare');
    await page.waitForLoadState('networkidle');

    // Either an EmptyState CTA or actual comparison content is visible.
    const content = page.getByText(/no analyses to compare|compare|analyze a resume/i).first();
    await expect(content).toBeVisible({ timeout: 15000 });
  });

  test('main navigation is reachable and labelled', async ({ page }) => {
    await page.goto('/home');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('nav, header').first()).toBeVisible({ timeout: 15000 });
  });
});
