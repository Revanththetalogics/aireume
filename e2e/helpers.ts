import { expect, type Page } from '@playwright/test';

/** Authenticated home/dashboard route (there is no `/home` route). */
export async function gotoDashboard(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('networkidle');
}

export async function expectAppShell(page: Page) {
  await expect(page.locator('nav, header').first()).toBeVisible({ timeout: 15000 });
}

export async function gotoAnalyze(page: Page) {
  await page.goto('/analyze');
  await page.waitForLoadState('networkidle');
}

export async function expectRequisitionPicker(page: Page) {
  await expect(page.getByText(/select an opening to start/i).first()).toBeVisible({
    timeout: 15000,
  });
}

export async function selectFirstRequisitionOnAnalyze(page: Page): Promise<boolean> {
  await expectRequisitionPicker(page);
  const reqButton = page.locator('.grid.gap-2.max-h-80.overflow-y-auto button').first();
  if (!(await reqButton.isVisible({ timeout: 10000 }).catch(() => false))) {
    return false;
  }
  await reqButton.click();
  await expect(page.getByText(/screening for/i).first()).toBeVisible({ timeout: 15000 });
  return true;
}

export async function enableAdHocScreeningIfAvailable(page: Page): Promise<boolean> {
  const link = page.getByRole('button', { name: /quick screen without a requisition/i });
  if (!(await link.isVisible({ timeout: 3000 }).catch(() => false))) {
    return false;
  }
  await link.click();
  await expect(page.locator('textarea').first()).toBeVisible({ timeout: 10000 });
  return true;
}

export function apiBaseUrl(): string {
  return (
    process.env.PLAYWRIGHT_API_URL
    || process.env.PLAYWRIGHT_BASE_URL
    || 'https://airesume-staging.thetalogics.com'
  ).replace(/\/$/, '');
}

export async function isE2eTestApiAvailable(request: import('@playwright/test').APIRequestContext): Promise<boolean> {
  try {
    const resp = await request.post(`${apiBaseUrl()}/api/auth/test/verify-email`, {
      data: { email: 'e2e-probe@example.com' },
    });
    return resp.status() !== 404;
  } catch {
    return false;
  }
}
